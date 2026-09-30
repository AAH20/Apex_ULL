/*
 * ULL Network Stack — C Header
 * ============================
 * Ultra-low-latency network stack with DPDK-style kernel bypass,
 * RDMA-inspired zero-copy, and lock-free data paths.
 *
 * Architecture:
 *   - Packet buffer pool: hugepage-backed, zero-copy, cache-aligned
 *   - TX/RX rings: SPSC lock-free (no CAS on fast path)
 *   - Queue pairs: RDMA-style QP abstraction for connection management
 *   - Completion queues: lock-free CQ for TX/RX completions
 *   - Poll-mode: no interrupts, pure polling for determinism
 *
 * Build:  clang -O3 -march=native -shared -fPIC -o libnetstack.so net_stack.c
 */

#ifndef ULL_NET_STACK_H
#define ULL_NET_STACK_H

#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ================================================================== */
/* Constants                                                           */
/* ================================================================== */

#define NET_CACHE_LINE_SIZE     64
#define NET_MAX_PORTS          16
#define NET_MAX_QP_PER_PORT    256
#define NET_MAX_CQ_PER_PORT    256
#define NET_DEFAULT_RING_SIZE  4096
#define NET_MAX_PKT_SIZE       9000   /* jumbo frame */
#define NET_MIN_PKT_SIZE       64
#define NET_MAX_BUFFERS        (1UL << 20)  /* 1M buffers */
#define NET_PKT_POOL_SIZE      (1UL << 16)  /* 64K packets per pool */
#define NET_MAX_SGE            16     /* scatter-gather entries per WR */

/* ================================================================== */
/* Cache alignment macros                                               */
/* ================================================================== */

#define NET_CACHE_ALIGN(x) \
    (((x) + NET_CACHE_LINE_SIZE - 1) & ~(NET_CACHE_LINE_SIZE - 1))

#define NET_ALIGNED __attribute__((aligned(NET_CACHE_LINE_SIZE)))

/* ================================================================== */
/* Packet buffer (zero-copy)                                           */
/* ================================================================== */

/*
 * Packet buffer descriptor. The actual data lives in a separate
 * hugepage-backed pool; this descriptor is the only thing that
 * moves through rings — true zero-copy.
 */
typedef struct {
    uint32_t index;          /* index into buffer pool */
    uint16_t length;         /* actual packet length */
    uint16_t flags;          /* NET_FLAG_* */
    uint64_t timestamp_ns;   /* RX timestamp (set by NIC) */
    uint64_t user_data;      /* opaque user context */
} net_buf_t;

/* Buffer flags */
#define NET_FLAG_RX             0x0001
#define NET_FLAG_TX             0x0002
#define NET_FLAG_HW_TIMESTAMP   0x0004
#define NET_FLAG_HW_CSUM        0x0008
#define NET_FLAG_INLINE         0x0010  /* data inline in descriptor */
#define NET_FLAG_MULTI_SGE      0x0020  /* scatter-gather */

/* ================================================================== */
/* Packet buffer pool                                                  */
/* ================================================================== */

typedef struct {
    /* Buffer metadata array (cache-aligned) */
    net_buf_t * NET_ALIGNED bufs;

    /* Data pool: contiguous hugepage-backed memory */
    void * NET_ALIGNED data_pool;
    uint32_t data_pool_size;     /* total bytes */
    uint32_t buf_size;           /* bytes per buffer (incl. headroom) */

    /* Free stack (LIFO, lock-free) */
    _Atomic uint32_t NET_ALIGNED free_head;
    uint32_t * NET_ALIGNED free_stack;
    uint32_t capacity;

    /* Stats */
    _Atomic uint64_t alloc_count;
    _Atomic uint64_t free_count;
} net_buf_pool_t;

int  net_buf_pool_init(net_buf_pool_t *pool, uint32_t capacity, uint32_t buf_size);
void net_buf_pool_destroy(net_buf_pool_t *pool);
net_buf_t *net_buf_alloc(net_buf_pool_t *pool);
void net_buf_free(net_buf_pool_t *pool, net_buf_t *buf);
uint32_t net_buf_pool_free_count(const net_buf_pool_t *pool);

/* ================================================================== */
/* SPSC TX/RX ring (lock-free, no CAS on fast path)                    */
/* ================================================================== */

typedef struct {
    /* Producer-owned */
    _Atomic uint64_t NET_ALIGNED head;
    uint64_t _pad1[7];

    /* Consumer-owned */
    _Atomic uint64_t NET_ALIGNED tail;
    uint64_t _pad2[7];

    /* Shared */
    uint64_t mask;
    uint64_t capacity;
    net_buf_t ** NET_ALIGNED ring;
} net_ring_t;

int  net_ring_init(net_ring_t *r, uint64_t capacity);
void net_ring_destroy(net_ring_t *r);
bool net_ring_push(net_ring_t *r, net_buf_t *buf);
bool net_ring_pop(net_ring_t *r, net_buf_t **buf);
bool net_ring_is_empty(const net_ring_t *r);
bool net_ring_is_full(const net_ring_t *r);
uint64_t net_ring_size(const net_ring_t *r);

/* Batch operations */
uint64_t net_ring_push_batch(net_ring_t *r, net_buf_t **bufs, uint64_t n);
uint64_t net_ring_pop_batch(net_ring_t *r, net_buf_t **bufs, uint64_t n);

/* ================================================================== */
/* Completion queue (SPSC, lock-free)                                  */
/* ================================================================== */

typedef enum {
    NET_CQ_OK = 0,
    NET_CQ_ERROR = 1,
    NET_CQ_TRUNCATED = 2,
} net_cq_status_t;

typedef struct {
    net_buf_t *buf;
    net_cq_status_t status;
    uint32_t length;
    uint64_t timestamp_ns;
} net_cqe_t;

typedef struct {
    _Atomic uint64_t NET_ALIGNED head;
    uint64_t _pad1[7];

    _Atomic uint64_t NET_ALIGNED tail;
    uint64_t _pad2[7];

    uint64_t mask;
    uint64_t capacity;
    net_cqe_t * NET_ALIGNED ring;
} net_cq_t;

int  net_cq_init(net_cq_t *cq, uint64_t capacity);
void net_cq_destroy(net_cq_t *cq);
bool net_cq_push(net_cq_t *cq, const net_cqe_t *cqe);
bool net_cq_pop(net_cq_t *cq, net_cqe_t *cqe);

/* ================================================================== */
/* Queue Pair (RDMA-style connection abstraction)                       */
/* ================================================================== */

typedef enum {
    NET_QP_RESET = 0,
    NET_QP_INIT,
    NET_QP_RTR,   /* ready to receive */
    NET_QP_RTS,   /* ready to send */
    NET_QP_ERROR,
} net_qp_state_t;

typedef struct {
    uint32_t qp_num;
    net_qp_state_t state;

    /* TX path */
    net_ring_t tx_ring;
    net_cq_t tx_cq;

    /* RX path */
    net_ring_t rx_ring;
    net_cq_t rx_cq;

    /* Shared buffer pool */
    net_buf_pool_t *pool;

    /* Stats */
    _Atomic uint64_t tx_pkts;
    _Atomic uint64_t tx_bytes;
    _Atomic uint64_t rx_pkts;
    _Atomic uint64_t rx_bytes;
    _Atomic uint64_t tx_errors;
    _Atomic uint64_t rx_errors;
} net_qp_t;

int  net_qp_init(net_qp_t *qp, uint32_t qp_num, net_buf_pool_t *pool,
                uint64_t ring_size);
void net_qp_destroy(net_qp_t *qp);
bool net_qp_send(net_qp_t *qp, net_buf_t *buf);
bool net_qp_recv(net_qp_t *qp, net_buf_t **buf);
bool net_qp_poll_tx(net_qp_t *qp, net_cqe_t *cqe);
bool net_qp_poll_rx(net_qp_t *qp, net_cqe_t *cqe);
uint64_t net_qp_loopback(net_qp_t *qp);

/* ================================================================== */
/* Port / NIC abstraction                                              */
/* ================================================================== */

typedef struct {
    uint32_t port_id;
    char name[32];

    /* Hardware info */
    uint64_t mac_addr;
    uint32_t mtu;
    uint64_t link_speed;     /* bits per second */
    bool link_up;

    /* Buffer pool */
    net_buf_pool_t pool;

    /* Queue pairs */
    net_qp_t * NET_ALIGNED qps[NET_MAX_QP_PER_PORT];
    uint32_t num_qps;

    /* Stats */
    _Atomic uint64_t rx_pkts;
    _Atomic uint64_t tx_pkts;
    _Atomic uint64_t rx_bytes;
    _Atomic uint64_t tx_bytes;
    _Atomic uint64_t rx_dropped;
    _Atomic uint64_t tx_dropped;
} net_port_t;

int  net_port_init(net_port_t *port, uint32_t port_id, const char *name,
                  uint32_t pool_capacity, uint32_t buf_size);
void net_port_destroy(net_port_t *port);
net_qp_t *net_port_create_qp(net_port_t *port, uint32_t qp_num,
                             uint64_t ring_size);
bool net_port_rx_burst(net_port_t *port, uint32_t qp_num,
                       net_buf_t **bufs, uint32_t max_pkts);
bool net_port_tx_burst(net_port_t *port, uint32_t qp_num,
                       net_buf_t **bufs, uint32_t n);

/* ================================================================== */
/* Network stack (top-level)                                           */
/* ================================================================== */

typedef struct {
    net_port_t ports[NET_MAX_PORTS];
    uint32_t num_ports;

    /* Global stats */
    _Atomic uint64_t total_rx_pkts;
    _Atomic uint64_t total_tx_pkts;
    _Atomic uint64_t total_rx_bytes;
    _Atomic uint64_t total_tx_bytes;
    _Atomic uint64_t total_rx_dropped;
    _Atomic uint64_t total_tx_dropped;
} net_stack_t;

int  net_stack_init(net_stack_t *stack, uint32_t num_ports);
void net_stack_destroy(net_stack_t *stack);
net_port_t *net_stack_get_port(net_stack_t *stack, uint32_t port_id);

/* ================================================================== */
/* Utility functions                                                   */
/* ================================================================== */

static inline uint64_t net_now_ns(void) {
#if defined(__APPLE__)
    extern uint64_t net_mach_now(void);
    return net_mach_now();
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
#endif
}

static inline void net_cpu_pause(void) {
#if defined(__x86_64__) || defined(__i386__)
    __builtin_ia32_pause();
#elif defined(__aarch64__)
    __asm__ volatile("yield" ::: "memory");
#else
    __asm__ volatile("" ::: "memory");
#endif
}

#define net_compiler_barrier() __asm__ volatile("" ::: "memory")
#define net_memory_barrier() __atomic_thread_fence(__ATOMIC_SEQ_CST)
#define net_acquire_barrier() __atomic_thread_fence(__ATOMIC_ACQUIRE)
#define net_release_barrier() __atomic_thread_fence(__ATOMIC_RELEASE)

#ifdef __cplusplus
}
#endif

#endif /* ULL_NET_STACK_H */
