/*
 * ULL Network Stack — C Implementation
 * ====================================
 * Ultra-low-latency network stack with kernel bypass, zero-copy,
 * and lock-free data paths.
 *
 * Key design principles:
 * - Zero-copy: packet buffers are allocated once from hugepage-backed
 *   pools and never copied — only descriptors move through rings.
 * - Lock-free: SPSC rings use relaxed atomics on the fast path (no CAS).
 * - Cache-line alignment: all shared state is padded to prevent false sharing.
 * - Poll-mode: no interrupts; pure polling for deterministic latency.
 * - Batch operations: amortize atomic overhead across multiple packets.
 */

#include "net_stack.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>

#if defined(__APPLE__)
#include <mach/mach_time.h>
static mach_timebase_info_data_t _net_timebase = {0, 0};
static int _net_timebase_init = 0;
#endif

/* ================================================================== */
/* Internal helpers                                                    */
/* ================================================================== */

static inline uint64_t next_pow2(uint64_t n) {
    if (n < 16) n = 16;
    n--;
    n |= n >> 1;
    n |= n >> 2;
    n |= n >> 4;
    n |= n >> 8;
    n |= n >> 16;
    n |= n >> 32;
    n++;
    return n;
}

static inline void *alloc_cache_aligned(size_t size) {
    void *ptr = NULL;
#if defined(__APPLE__)
    ptr = aligned_alloc(NET_CACHE_LINE_SIZE, size);
#elif defined(_WIN32)
    ptr = _aligned_malloc(size, NET_CACHE_LINE_SIZE);
#else
    if (posix_memalign(&ptr, NET_CACHE_LINE_SIZE, size) != 0) return NULL;
#endif
    return ptr;
}

/* ================================================================== */
/* High-resolution timer                                               */
/* ================================================================== */

#if defined(__APPLE__)
uint64_t net_mach_now(void) {
    if (!_net_timebase_init) {
        mach_timebase_info(&_net_timebase);
        _net_timebase_init = 1;
    }
    uint64_t t = mach_absolute_time();
    return t * _net_timebase.numer / _net_timebase.denom;
}
#endif

uint64_t net_now_ns_export(void) {
    return net_now_ns();
}

/* ================================================================== */
/* Packet buffer pool                                                  */
/* ================================================================== */

int net_buf_pool_init(net_buf_pool_t *pool, uint32_t capacity, uint32_t buf_size) {
    if (!pool) return -1;
    if (capacity > NET_MAX_BUFFERS) return -1;
    if (buf_size < NET_MIN_PKT_SIZE) buf_size = NET_MIN_PKT_SIZE;
    if (buf_size > NET_MAX_PKT_SIZE) buf_size = NET_MAX_PKT_SIZE;

    /* Allocate buffer descriptor array */
    pool->bufs = (net_buf_t *)alloc_cache_aligned(capacity * sizeof(net_buf_t));
    if (!pool->bufs) return -1;

    /* Allocate data pool: contiguous memory for all packet data */
    pool->data_pool_size = (uint64_t)capacity * buf_size;
    pool->data_pool = alloc_cache_aligned(pool->data_pool_size);
    if (!pool->data_pool) {
        free(pool->bufs);
        return -1;
    }

    /* Allocate free stack */
    pool->free_stack = (uint32_t *)alloc_cache_aligned(capacity * sizeof(uint32_t));
    if (!pool->free_stack) {
        free(pool->data_pool);
        free(pool->bufs);
        return -1;
    }

    /* Initialize all buffers as free */
    for (uint32_t i = 0; i < capacity; i++) {
        pool->bufs[i].index = i;
        pool->bufs[i].length = 0;
        pool->bufs[i].flags = 0;
        pool->bufs[i].timestamp_ns = 0;
        pool->bufs[i].user_data = 0;
        pool->free_stack[i] = capacity - 1 - i;  /* LIFO order */
    }

    atomic_init(&pool->free_head, capacity);
    pool->capacity = capacity;
    pool->buf_size = buf_size;
    atomic_init(&pool->alloc_count, 0);
    atomic_init(&pool->free_count, 0);

    return 0;
}

void net_buf_pool_destroy(net_buf_pool_t *pool) {
    if (!pool) return;
    free(pool->free_stack);
    free(pool->data_pool);
    free(pool->bufs);
    pool->free_stack = NULL;
    pool->data_pool = NULL;
    pool->bufs = NULL;
}

net_buf_t *net_buf_alloc(net_buf_pool_t *pool) {
    if (!pool) return NULL;

    uint32_t head = atomic_load_explicit(&pool->free_head, __ATOMIC_ACQUIRE);
    if (head == 0) return NULL;  /* pool exhausted */

    /* Pop from free stack (LIFO) */
    uint32_t idx = pool->free_stack[head - 1];
    atomic_store_explicit(&pool->free_head, head - 1, __ATOMIC_RELEASE);

    atomic_fetch_add_explicit(&pool->alloc_count, 1, __ATOMIC_RELAXED);
    return &pool->bufs[idx];
}

void net_buf_free(net_buf_pool_t *pool, net_buf_t *buf) {
    if (!pool || !buf) return;

    uint32_t idx = buf->index;
    uint32_t head = atomic_load_explicit(&pool->free_head, __ATOMIC_ACQUIRE);
    if (head >= pool->capacity) return;  /* shouldn't happen */

    /* Push onto free stack */
    pool->free_stack[head] = idx;
    atomic_store_explicit(&pool->free_head, head + 1, __ATOMIC_RELEASE);

    atomic_fetch_add_explicit(&pool->free_count, 1, __ATOMIC_RELAXED);
}

uint32_t net_buf_pool_free_count(const net_buf_pool_t *pool) {
    if (!pool) return 0;
    return atomic_load_explicit(&pool->free_head, __ATOMIC_ACQUIRE);
}

/* ================================================================== */
/* SPSC Ring Buffer                                                    */
/* ================================================================== */

int net_ring_init(net_ring_t *r, uint64_t capacity) {
    if (!r) return -1;
    capacity = next_pow2(capacity);

    r->ring = (net_buf_t **)alloc_cache_aligned(capacity * sizeof(net_buf_t *));
    if (!r->ring) return -1;

    memset(r->ring, 0, capacity * sizeof(net_buf_t *));
    atomic_init(&r->head, 0);
    atomic_init(&r->tail, 0);
    r->mask = capacity - 1;
    r->capacity = capacity;
    return 0;
}

void net_ring_destroy(net_ring_t *r) {
    if (!r) return;
    free(r->ring);
    r->ring = NULL;
}

bool net_ring_push(net_ring_t *r, net_buf_t *buf) {
    const uint64_t h = atomic_load_explicit(&r->head, __ATOMIC_RELAXED);
    const uint64_t next = h + 1;

    /* Full check */
    if (next - atomic_load_explicit(&r->tail, __ATOMIC_ACQUIRE) >= r->capacity) {
        return false;
    }

    r->ring[h & r->mask] = buf;
    atomic_store_explicit(&r->head, next, __ATOMIC_RELEASE);
    return true;
}

bool net_ring_pop(net_ring_t *r, net_buf_t **buf) {
    const uint64_t t = atomic_load_explicit(&r->tail, __ATOMIC_RELAXED);

    if (t == atomic_load_explicit(&r->head, __ATOMIC_ACQUIRE)) {
        return false;  /* empty */
    }

    *buf = r->ring[t & r->mask];
    atomic_store_explicit(&r->tail, t + 1, __ATOMIC_RELEASE);
    return true;
}

bool net_ring_is_empty(const net_ring_t *r) {
    return atomic_load_explicit(&r->head, __ATOMIC_ACQUIRE) ==
           atomic_load_explicit(&r->tail, __ATOMIC_ACQUIRE);
}

bool net_ring_is_full(const net_ring_t *r) {
    const uint64_t h = atomic_load_explicit(&r->head, __ATOMIC_ACQUIRE);
    const uint64_t t = atomic_load_explicit(&r->tail, __ATOMIC_ACQUIRE);
    return (h - t) >= r->capacity;
}

uint64_t net_ring_size(const net_ring_t *r) {
    const uint64_t h = atomic_load_explicit(&r->head, __ATOMIC_ACQUIRE);
    const uint64_t t = atomic_load_explicit(&r->tail, __ATOMIC_ACQUIRE);
    return h - t;
}

uint64_t net_ring_push_batch(net_ring_t *r, net_buf_t **bufs, uint64_t n) {
    const uint64_t h = atomic_load_explicit(&r->head, __ATOMIC_RELAXED);
    const uint64_t t = atomic_load_explicit(&r->tail, __ATOMIC_ACQUIRE);
    const uint64_t avail = r->capacity - (h - t);
    if (n > avail) n = avail;
    if (n == 0) return 0;

    const uint64_t idx = h & r->mask;
    if (idx + n <= r->capacity) {
        memcpy(&r->ring[idx], bufs, n * sizeof(net_buf_t *));
    } else {
        const uint64_t first = r->capacity - idx;
        memcpy(&r->ring[idx], bufs, first * sizeof(net_buf_t *));
        memcpy(r->ring, &bufs[first], (n - first) * sizeof(net_buf_t *));
    }
    atomic_store_explicit(&r->head, h + n, __ATOMIC_RELEASE);
    return n;
}

uint64_t net_ring_pop_batch(net_ring_t *r, net_buf_t **bufs, uint64_t n) {
    const uint64_t t = atomic_load_explicit(&r->tail, __ATOMIC_RELAXED);
    const uint64_t h = atomic_load_explicit(&r->head, __ATOMIC_ACQUIRE);
    const uint64_t avail = h - t;
    if (n > avail) n = avail;
    if (n == 0) return 0;

    const uint64_t idx = t & r->mask;
    if (idx + n <= r->capacity) {
        memcpy(bufs, &r->ring[idx], n * sizeof(net_buf_t *));
    } else {
        const uint64_t first = r->capacity - idx;
        memcpy(bufs, &r->ring[idx], first * sizeof(net_buf_t *));
        memcpy(&bufs[first], r->ring, (n - first) * sizeof(net_buf_t *));
    }
    atomic_store_explicit(&r->tail, t + n, __ATOMIC_RELEASE);
    return n;
}

/* ================================================================== */
/* Completion Queue                                                    */
/* ================================================================== */

int net_cq_init(net_cq_t *cq, uint64_t capacity) {
    if (!cq) return -1;
    capacity = next_pow2(capacity);

    cq->ring = (net_cqe_t *)alloc_cache_aligned(capacity * sizeof(net_cqe_t));
    if (!cq->ring) return -1;

    memset(cq->ring, 0, capacity * sizeof(net_cqe_t));
    atomic_init(&cq->head, 0);
    atomic_init(&cq->tail, 0);
    cq->mask = capacity - 1;
    cq->capacity = capacity;
    return 0;
}

void net_cq_destroy(net_cq_t *cq) {
    if (!cq) return;
    free(cq->ring);
    cq->ring = NULL;
}

bool net_cq_push(net_cq_t *cq, const net_cqe_t *cqe) {
    const uint64_t h = atomic_load_explicit(&cq->head, __ATOMIC_RELAXED);
    const uint64_t next = h + 1;

    if (next - atomic_load_explicit(&cq->tail, __ATOMIC_ACQUIRE) >= cq->capacity) {
        return false;
    }

    cq->ring[h & cq->mask] = *cqe;
    atomic_store_explicit(&cq->head, next, __ATOMIC_RELEASE);
    return true;
}

bool net_cq_pop(net_cq_t *cq, net_cqe_t *cqe) {
    const uint64_t t = atomic_load_explicit(&cq->tail, __ATOMIC_RELAXED);

    if (t == atomic_load_explicit(&cq->head, __ATOMIC_ACQUIRE)) {
        return false;
    }

    *cqe = cq->ring[t & cq->mask];
    atomic_store_explicit(&cq->tail, t + 1, __ATOMIC_RELEASE);
    return true;
}

/* ================================================================== */
/* Queue Pair                                                          */
/* ================================================================== */

int net_qp_init(net_qp_t *qp, uint32_t qp_num, net_buf_pool_t *pool,
                uint64_t ring_size) {
    if (!qp || !pool) return -1;

    qp->qp_num = qp_num;
    qp->state = NET_QP_RESET;
    qp->pool = pool;

    if (net_ring_init(&qp->tx_ring, ring_size) != 0) return -1;
    if (net_ring_init(&qp->rx_ring, ring_size) != 0) {
        net_ring_destroy(&qp->tx_ring);
        return -1;
    }
    if (net_cq_init(&qp->tx_cq, ring_size) != 0) {
        net_ring_destroy(&qp->tx_ring);
        net_ring_destroy(&qp->rx_ring);
        return -1;
    }
    if (net_cq_init(&qp->rx_cq, ring_size) != 0) {
        net_ring_destroy(&qp->tx_ring);
        net_ring_destroy(&qp->rx_ring);
        net_cq_destroy(&qp->tx_cq);
        return -1;
    }

    atomic_init(&qp->tx_pkts, 0);
    atomic_init(&qp->tx_bytes, 0);
    atomic_init(&qp->rx_pkts, 0);
    atomic_init(&qp->rx_bytes, 0);
    atomic_init(&qp->tx_errors, 0);
    atomic_init(&qp->rx_errors, 0);

    qp->state = NET_QP_RTS;
    return 0;
}

void net_qp_destroy(net_qp_t *qp) {
    if (!qp) return;
    net_ring_destroy(&qp->tx_ring);
    net_ring_destroy(&qp->rx_ring);
    net_cq_destroy(&qp->tx_cq);
    net_cq_destroy(&qp->rx_cq);
    qp->state = NET_QP_RESET;
}

bool net_qp_send(net_qp_t *qp, net_buf_t *buf) {
    if (!qp || !buf) return false;
    if (qp->state != NET_QP_RTS) return false;

    buf->flags |= NET_FLAG_TX;
    if (!net_ring_push(&qp->tx_ring, buf)) {
        atomic_fetch_add_explicit(&qp->tx_errors, 1, __ATOMIC_RELAXED);
        return false;
    }

    atomic_fetch_add_explicit(&qp->tx_pkts, 1, __ATOMIC_RELAXED);
    atomic_fetch_add_explicit(&qp->tx_bytes, buf->length, __ATOMIC_RELAXED);
    return true;
}

bool net_qp_recv(net_qp_t *qp, net_buf_t **buf) {
    if (!qp || !buf) return false;

    if (!net_ring_pop(&qp->rx_ring, buf)) {
        return false;
    }

    atomic_fetch_add_explicit(&qp->rx_pkts, 1, __ATOMIC_RELAXED);
    atomic_fetch_add_explicit(&qp->rx_bytes, (*buf)->length, __ATOMIC_RELAXED);
    return true;
}

bool net_qp_poll_tx(net_qp_t *qp, net_cqe_t *cqe) {
    if (!qp || !cqe) return false;
    return net_cq_pop(&qp->tx_cq, cqe);
}

bool net_qp_poll_rx(net_qp_t *qp, net_cqe_t *cqe) {
    if (!qp || !cqe) return false;
    return net_cq_pop(&qp->rx_cq, cqe);
}

uint64_t net_qp_loopback(net_qp_t *qp) {
    if (!qp) return 0;
    uint64_t count = 0;
    net_buf_t *buf;
    while (net_ring_pop(&qp->tx_ring, &buf)) {
        if (!net_ring_push(&qp->rx_ring, buf)) {
            /* RX ring full, put it back */
            net_ring_push(&qp->tx_ring, buf);
            break;
        }
        count++;
    }
    return count;
}

/* ================================================================== */
/* Port / NIC                                                          */
/* ================================================================== */

int net_port_init(net_port_t *port, uint32_t port_id, const char *name,
                  uint32_t pool_capacity, uint32_t buf_size) {
    if (!port) return -1;

    port->port_id = port_id;
    strncpy(port->name, name, sizeof(port->name) - 1);
    port->name[sizeof(port->name) - 1] = '\0';
    port->mac_addr = 0;
    port->mtu = 1500;
    port->link_speed = 10000000000ULL;  /* 10 Gbps default */
    port->link_up = true;
    port->num_qps = 0;

    if (net_buf_pool_init(&port->pool, pool_capacity, buf_size) != 0) {
        return -1;
    }

    for (int i = 0; i < NET_MAX_QP_PER_PORT; i++) {
        port->qps[i] = NULL;
    }

    atomic_init(&port->rx_pkts, 0);
    atomic_init(&port->tx_pkts, 0);
    atomic_init(&port->rx_bytes, 0);
    atomic_init(&port->tx_bytes, 0);
    atomic_init(&port->rx_dropped, 0);
    atomic_init(&port->tx_dropped, 0);

    return 0;
}

void net_port_destroy(net_port_t *port) {
    if (!port) return;

    for (uint32_t i = 0; i < port->num_qps; i++) {
        if (port->qps[i]) {
            net_qp_destroy(port->qps[i]);
            free(port->qps[i]);
            port->qps[i] = NULL;
        }
    }
    net_buf_pool_destroy(&port->pool);
}

net_qp_t *net_port_create_qp(net_port_t *port, uint32_t qp_num,
                             uint64_t ring_size) {
    if (!port || port->num_qps >= NET_MAX_QP_PER_PORT) return NULL;

    net_qp_t *qp = (net_qp_t *)alloc_cache_aligned(sizeof(net_qp_t));
    if (!qp) return NULL;

    if (net_qp_init(qp, qp_num, &port->pool, ring_size) != 0) {
        free(qp);
        return NULL;
    }

    port->qps[port->num_qps++] = qp;
    return qp;
}

bool net_port_rx_burst(net_port_t *port, uint32_t qp_num,
                       net_buf_t **bufs, uint32_t max_pkts) {
    if (!port || !bufs || max_pkts == 0) return false;

    /* Find QP */
    net_qp_t *qp = NULL;
    for (uint32_t i = 0; i < port->num_qps; i++) {
        if (port->qps[i] && port->qps[i]->qp_num == qp_num) {
            qp = port->qps[i];
            break;
        }
    }
    if (!qp) return false;

    /* In a real implementation, this would read from NIC DMA */
    /* For now, we just poll the RX ring */
    uint32_t count = 0;
    while (count < max_pkts && net_ring_pop(&qp->rx_ring, &bufs[count])) {
        count++;
    }

    atomic_fetch_add_explicit(&port->rx_pkts, count, __ATOMIC_RELAXED);
    return count > 0;
}

bool net_port_tx_burst(net_port_t *port, uint32_t qp_num,
                       net_buf_t **bufs, uint32_t n) {
    if (!port || !bufs || n == 0) return false;

    net_qp_t *qp = NULL;
    for (uint32_t i = 0; i < port->num_qps; i++) {
        if (port->qps[i] && port->qps[i]->qp_num == qp_num) {
            qp = port->qps[i];
            break;
        }
    }
    if (!qp) return false;

    /* Push to TX ring */
    uint32_t sent = 0;
    for (uint32_t i = 0; i < n; i++) {
        if (net_ring_push(&qp->tx_ring, bufs[i])) {
            sent++;
        } else {
            atomic_fetch_add_explicit(&port->tx_dropped, 1, __ATOMIC_RELAXED);
        }
    }

    atomic_fetch_add_explicit(&port->tx_pkts, sent, __ATOMIC_RELAXED);
    return sent > 0;
}

/* ================================================================== */
/* Network Stack                                                       */
/* ================================================================== */

int net_stack_init(net_stack_t *stack, uint32_t num_ports) {
    if (!stack) return -1;
    if (num_ports > NET_MAX_PORTS) num_ports = NET_MAX_PORTS;

    stack->num_ports = num_ports;
    for (uint32_t i = 0; i < num_ports; i++) {
        /* Initialize each port with default settings */
        char name[32];
        snprintf(name, sizeof(name), "eth%u", i);
        if (net_port_init(&stack->ports[i], i, name,
                          NET_PKT_POOL_SIZE, NET_MAX_PKT_SIZE) != 0) {
            return -1;
        }
    }

    atomic_init(&stack->total_rx_pkts, 0);
    atomic_init(&stack->total_tx_pkts, 0);
    atomic_init(&stack->total_rx_bytes, 0);
    atomic_init(&stack->total_tx_bytes, 0);
    atomic_init(&stack->total_rx_dropped, 0);
    atomic_init(&stack->total_tx_dropped, 0);

    return 0;
}

void net_stack_destroy(net_stack_t *stack) {
    if (!stack) return;
    for (uint32_t i = 0; i < stack->num_ports; i++) {
        net_port_destroy(&stack->ports[i]);
    }
}

net_port_t *net_stack_get_port(net_stack_t *stack, uint32_t port_id) {
    if (!stack || port_id >= stack->num_ports) return NULL;
    return &stack->ports[port_id];
}
