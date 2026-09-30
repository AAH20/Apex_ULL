/*
 * ULL Queue Optimization Kernel — C Implementation
 * =================================================
 * Lock-free ring buffer implementations optimized for ultra-low latency.
 *
 * Key optimizations:
 * - Cache-line alignment prevents false sharing
 * - Power-of-2 ring sizes enable bitmask indexing (no modulo)
 * - SPSC uses relaxed atomics on fast path (no CAS)
 * - MPSC/MPMC use CAS only on the contended end
 * - Batch operations amortize atomic overhead
 * - Disruptor uses sequence barriers (no locks, no CAS on publish)
 */

#include "queue.h"

#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include <pthread.h>

#if defined(__APPLE__)
#include <mach/mach_time.h>
static mach_timebase_info_data_t _timebase = {0, 0};
static pthread_once_t _timebase_once = PTHREAD_ONCE_INIT;
static void init_timebase(void) { mach_timebase_info(&_timebase); }
#endif

/* ================================================================== */
/* Internal helpers                                                    */
/* ================================================================== */

static inline uint64_t next_pow2(uint64_t n) {
    if (n < QUEUE_MIN_SIZE) n = QUEUE_MIN_SIZE;
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
    ptr = aligned_alloc(CACHE_LINE_SIZE, size);
#elif defined(_WIN32)
    ptr = _aligned_malloc(size, CACHE_LINE_SIZE);
#else
    if (posix_memalign(&ptr, CACHE_LINE_SIZE, size) != 0) return NULL;
#endif
    return ptr;
}

/* ================================================================== */
/* High-resolution timer                                               */
/* ================================================================== */

#if defined(__APPLE__)
uint64_t ull_mach_now(void) {
    pthread_once(&_timebase_once, init_timebase);
    uint64_t t = mach_absolute_time();
    return t * _timebase.numer / _timebase.denom;
}
#endif

/* Non-inline wrapper so ctypes can find the symbol */
uint64_t ull_now_ns_export(void) {
    return ull_now_ns();
}

/* ================================================================== */
/* SPSC Ring Buffer                                                    */
/* ================================================================== */

int spsc_init(spsc_queue_t *q, uint64_t capacity) {
    if (!q || capacity > QUEUE_MAX_SIZE) return -1;
    capacity = next_pow2(capacity);
    if (capacity > QUEUE_MAX_SIZE) return -1;

    q->ring = (void **)alloc_cache_aligned(capacity * sizeof(void *));
    if (!q->ring) return -1;

    memset(q->ring, 0, capacity * sizeof(void *));
    atomic_init(&q->head, 0);
    atomic_init(&q->tail, 0);
    q->mask = capacity - 1;
    q->capacity = capacity;
    return 0;
}

void spsc_destroy(spsc_queue_t *q) {
    if (!q) return;
    free(q->ring);
    q->ring = NULL;
}

bool spsc_push(spsc_queue_t *q, void *item) {
    const uint64_t h = atomic_load_explicit(&q->head, __ATOMIC_RELAXED);
    const uint64_t next = h + 1;

    /* Full check: head - tail >= capacity */
    if (next - atomic_load_explicit(&q->tail, __ATOMIC_ACQUIRE) > q->capacity) {
        return false;
    }

    q->ring[h & q->mask] = item;
    atomic_store_explicit(&q->head, next, __ATOMIC_RELEASE);
    return true;
}

bool spsc_pop(spsc_queue_t *q, void **item) {
    const uint64_t t = atomic_load_explicit(&q->tail, __ATOMIC_RELAXED);

    if (t == atomic_load_explicit(&q->head, __ATOMIC_ACQUIRE)) {
        return false;  /* empty */
    }

    *item = q->ring[t & q->mask];
    atomic_store_explicit(&q->tail, t + 1, __ATOMIC_RELEASE);
    return true;
}

bool spsc_is_empty(const spsc_queue_t *q) {
    return atomic_load_explicit(&q->head, __ATOMIC_ACQUIRE) ==
           atomic_load_explicit(&q->tail, __ATOMIC_ACQUIRE);
}

bool spsc_is_full(const spsc_queue_t *q) {
    const uint64_t h = atomic_load_explicit(&q->head, __ATOMIC_ACQUIRE);
    const uint64_t t = atomic_load_explicit(&q->tail, __ATOMIC_ACQUIRE);
    return (h - t) >= q->capacity;
}

uint64_t spsc_size(const spsc_queue_t *q) {
    const uint64_t h = atomic_load_explicit(&q->head, __ATOMIC_ACQUIRE);
    const uint64_t t = atomic_load_explicit(&q->tail, __ATOMIC_ACQUIRE);
    return h - t;
}

uint64_t spsc_push_batch(spsc_queue_t *q, void **items, uint64_t n) {
    const uint64_t h = atomic_load_explicit(&q->head, __ATOMIC_RELAXED);
    const uint64_t t = atomic_load_explicit(&q->tail, __ATOMIC_ACQUIRE);
    const uint64_t avail = q->capacity - (h - t);
    if (n > avail) n = avail;
    if (n == 0) return 0;

    const uint64_t idx = h & q->mask;
    if (idx + n <= q->capacity) {
        memcpy(&q->ring[idx], items, n * sizeof(void *));
    } else {
        const uint64_t first = q->capacity - idx;
        memcpy(&q->ring[idx], items, first * sizeof(void *));
        memcpy(q->ring, &items[first], (n - first) * sizeof(void *));
    }
    atomic_store_explicit(&q->head, h + n, __ATOMIC_RELEASE);
    return n;
}

uint64_t spsc_pop_batch(spsc_queue_t *q, void **items, uint64_t n) {
    const uint64_t t = atomic_load_explicit(&q->tail, __ATOMIC_RELAXED);
    const uint64_t h = atomic_load_explicit(&q->head, __ATOMIC_ACQUIRE);
    const uint64_t avail = h - t;
    if (n > avail) n = avail;
    if (n == 0) return 0;

    const uint64_t idx = t & q->mask;
    if (idx + n <= q->capacity) {
        memcpy(items, &q->ring[idx], n * sizeof(void *));
    } else {
        const uint64_t first = q->capacity - idx;
        memcpy(items, &q->ring[idx], first * sizeof(void *));
        memcpy(&items[first], q->ring, (n - first) * sizeof(void *));
    }
    atomic_store_explicit(&q->tail, t + n, __ATOMIC_RELEASE);
    return n;
}

/* Bounded per-slot sequence queues. Payload is published only after writing it,
 * and a slot is reusable only after the consumer has copied its payload.
 * Reservation by a preempted thread can delay progress: no formal lock-free
 * progress guarantee is claimed. Init/destroy require quiescent ownership. */

int mpsc_init(mpsc_queue_t *q, uint64_t capacity) {
    if (!q || capacity > QUEUE_MAX_SIZE) return -1;
    capacity = next_pow2(capacity);
    q->ring = alloc_cache_aligned(capacity * sizeof(void *));
    q->sequence = alloc_cache_aligned(capacity * sizeof(*q->sequence));
    if (!q->ring || !q->sequence) { free(q->ring); free(q->sequence); q->ring = NULL; q->sequence = NULL; return -1; }
    atomic_init(&q->head, 0); atomic_init(&q->tail, 0);
    q->mask = capacity - 1; q->capacity = capacity;
    for (uint64_t i = 0; i < capacity; ++i) atomic_init(&q->sequence[i], i);
    return 0;
}
void mpsc_destroy(mpsc_queue_t *q) {
    if (!q) return;
    free(q->ring); free(q->sequence); q->ring = NULL; q->sequence = NULL;
}
bool mpsc_push(mpsc_queue_t *q, void *item) {
    uint64_t pos = atomic_load_explicit(&q->head, memory_order_relaxed);
    for (;;) {
        const uint64_t seq = atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire);
        const int64_t difference = (int64_t)(seq - pos);
        if (difference == 0) {
            if (atomic_compare_exchange_weak_explicit(&q->head, &pos, pos + 1, memory_order_relaxed, memory_order_relaxed)) break;
        } else if (difference < 0) return false;
        else pos = atomic_load_explicit(&q->head, memory_order_relaxed);
    }
    q->ring[pos & q->mask] = item;
    atomic_store_explicit(&q->sequence[pos & q->mask], pos + 1, memory_order_release);
    return true;
}
bool mpsc_pop(mpsc_queue_t *q, void **item) {
    if (!item) return false;
    uint64_t pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    for (;;) {
        const uint64_t seq = atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire);
        const int64_t difference = (int64_t)(seq - (pos + 1));
        if (difference == 0) {
            if (atomic_compare_exchange_weak_explicit(&q->tail, &pos, pos + 1, memory_order_relaxed, memory_order_relaxed)) break;
        } else if (difference < 0) return false;
        else pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    }
    *item = q->ring[pos & q->mask];
    atomic_store_explicit(&q->sequence[pos & q->mask], pos + q->capacity, memory_order_release);
    return true;
}
bool mpsc_is_empty(const mpsc_queue_t *q) {
    const uint64_t pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    return atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire) != pos + 1;
}
uint64_t mpsc_size(const mpsc_queue_t *q) {
    const uint64_t tail = atomic_load_explicit(&q->tail, memory_order_acquire);
    const uint64_t head = atomic_load_explicit(&q->head, memory_order_acquire);
    const uint64_t size = head - tail;
    return size > q->capacity ? q->capacity : size; // Approximate, includes reservations.
}

int mpmc_init(mpmc_queue_t *q, uint64_t capacity) {
    if (!q || capacity > QUEUE_MAX_SIZE) return -1;
    capacity = next_pow2(capacity);
    q->ring = alloc_cache_aligned(capacity * sizeof(void *));
    q->sequence = alloc_cache_aligned(capacity * sizeof(*q->sequence));
    if (!q->ring || !q->sequence) { free(q->ring); free(q->sequence); q->ring = NULL; q->sequence = NULL; return -1; }
    atomic_init(&q->head, 0); atomic_init(&q->tail, 0);
    q->mask = capacity - 1; q->capacity = capacity;
    for (uint64_t i = 0; i < capacity; ++i) atomic_init(&q->sequence[i], i);
    return 0;
}
void mpmc_destroy(mpmc_queue_t *q) {
    if (!q) return;
    free(q->ring); free(q->sequence); q->ring = NULL; q->sequence = NULL;
}
bool mpmc_push(mpmc_queue_t *q, void *item) {
    uint64_t pos = atomic_load_explicit(&q->head, memory_order_relaxed);
    for (;;) {
        const uint64_t seq = atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire);
        const int64_t difference = (int64_t)(seq - pos);
        if (difference == 0) {
            if (atomic_compare_exchange_weak_explicit(&q->head, &pos, pos + 1, memory_order_relaxed, memory_order_relaxed)) break;
        } else if (difference < 0) return false;
        else pos = atomic_load_explicit(&q->head, memory_order_relaxed);
    }
    q->ring[pos & q->mask] = item;
    atomic_store_explicit(&q->sequence[pos & q->mask], pos + 1, memory_order_release);
    return true;
}
bool mpmc_pop(mpmc_queue_t *q, void **item) {
    if (!item) return false;
    uint64_t pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    for (;;) {
        const uint64_t seq = atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire);
        const int64_t difference = (int64_t)(seq - (pos + 1));
        if (difference == 0) {
            if (atomic_compare_exchange_weak_explicit(&q->tail, &pos, pos + 1, memory_order_relaxed, memory_order_relaxed)) break;
        } else if (difference < 0) return false;
        else pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    }
    *item = q->ring[pos & q->mask];
    atomic_store_explicit(&q->sequence[pos & q->mask], pos + q->capacity, memory_order_release);
    return true;
}
bool mpmc_is_empty(const mpmc_queue_t *q) {
    const uint64_t pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    return atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire) != pos + 1;
}
uint64_t mpmc_size(const mpmc_queue_t *q) {
    const uint64_t tail = atomic_load_explicit(&q->tail, memory_order_acquire);
    const uint64_t head = atomic_load_explicit(&q->head, memory_order_acquire);
    const uint64_t size = head - tail;
    return size > q->capacity ? q->capacity : size; // Approximate, includes reservations.
}

int spmc_init(spmc_queue_t *q, uint64_t capacity) {
    if (!q || capacity > QUEUE_MAX_SIZE) return -1;
    capacity = next_pow2(capacity);
    q->ring = alloc_cache_aligned(capacity * sizeof(void *));
    q->sequence = alloc_cache_aligned(capacity * sizeof(*q->sequence));
    if (!q->ring || !q->sequence) { free(q->ring); free(q->sequence); q->ring = NULL; q->sequence = NULL; return -1; }
    atomic_init(&q->head, 0); atomic_init(&q->tail, 0);
    q->mask = capacity - 1; q->capacity = capacity;
    for (uint64_t i = 0; i < capacity; ++i) atomic_init(&q->sequence[i], i);
    return 0;
}
void spmc_destroy(spmc_queue_t *q) {
    if (!q) return;
    free(q->ring); free(q->sequence); q->ring = NULL; q->sequence = NULL;
}
bool spmc_push(spmc_queue_t *q, void *item) {
    uint64_t pos = atomic_load_explicit(&q->head, memory_order_relaxed);
    for (;;) {
        const uint64_t seq = atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire);
        const int64_t difference = (int64_t)(seq - pos);
        if (difference == 0) {
            if (atomic_compare_exchange_weak_explicit(&q->head, &pos, pos + 1, memory_order_relaxed, memory_order_relaxed)) break;
        } else if (difference < 0) return false;
        else pos = atomic_load_explicit(&q->head, memory_order_relaxed);
    }
    q->ring[pos & q->mask] = item;
    atomic_store_explicit(&q->sequence[pos & q->mask], pos + 1, memory_order_release);
    return true;
}
bool spmc_pop(spmc_queue_t *q, void **item) {
    if (!item) return false;
    uint64_t pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    for (;;) {
        const uint64_t seq = atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire);
        const int64_t difference = (int64_t)(seq - (pos + 1));
        if (difference == 0) {
            if (atomic_compare_exchange_weak_explicit(&q->tail, &pos, pos + 1, memory_order_relaxed, memory_order_relaxed)) break;
        } else if (difference < 0) return false;
        else pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    }
    *item = q->ring[pos & q->mask];
    atomic_store_explicit(&q->sequence[pos & q->mask], pos + q->capacity, memory_order_release);
    return true;
}
bool spmc_is_empty(const spmc_queue_t *q) {
    const uint64_t pos = atomic_load_explicit(&q->tail, memory_order_relaxed);
    return atomic_load_explicit(&q->sequence[pos & q->mask], memory_order_acquire) != pos + 1;
}
uint64_t spmc_size(const spmc_queue_t *q) {
    const uint64_t tail = atomic_load_explicit(&q->tail, memory_order_acquire);
    const uint64_t head = atomic_load_explicit(&q->head, memory_order_acquire);
    const uint64_t size = head - tail;
    return size > q->capacity ? q->capacity : size; // Approximate, includes reservations.
}

/* ================================================================== */
/* LMAX Disruptor                                                      */
/* ================================================================== */

/* The previous placeholder published cursor before payload and had no barrier.
 * Refuse to initialize rather than expose an unsafe working-looking backend. */
int disruptor_init(disruptor_t *d, uint64_t capacity) { (void)capacity; if (d) memset(d, 0, sizeof(*d)); errno = ENOTSUP; return -1; }
void disruptor_destroy(disruptor_t *d) { (void)d; }
bool disruptor_register_consumer(disruptor_t *d, uint32_t id, disruptor_event_handler_t handler, void *ctx) { (void)d; (void)id; (void)handler; (void)ctx; return false; }
uint64_t disruptor_next_sequence(disruptor_t *d) { (void)d; return 0; }
bool disruptor_claim(disruptor_t *d, uint64_t *seq) { (void)d; (void)seq; return false; }
bool disruptor_publish(disruptor_t *d, void *event) { (void)d; (void)event; return false; }
void disruptor_commit(disruptor_t *d, uint64_t seq) { (void)d; (void)seq; }

/* ================================================================== */
/* Custom ULL Queue (hybrid)                                           */
/* ================================================================== */

int ull_queue_init(ull_queue_t *q, uint64_t capacity) {
    if (!q) return -1;
    if (spsc_init(&q->spsc, capacity) != 0) return -1;
    if (mpmc_init(&q->mpmc, capacity) != 0) {
        spsc_destroy(&q->spsc);
        return -1;
    }
    q->mode = 0;  /* auto */
    atomic_init(&q->use_count, 0);
    return 0;
}

void ull_queue_destroy(ull_queue_t *q) {
    if (!q) return;
    spsc_destroy(&q->spsc);
    mpmc_destroy(&q->mpmc);
}

bool ull_queue_push(ull_queue_t *q, void *item) {
    if (!q) return false;

    if (q->mode == 1) {
        return spsc_push(&q->spsc, item);
    } else if (q->mode == 2) {
        return mpmc_push(&q->mpmc, item);
    }

    // Auto mode stays on one MPMC queue; splitting queues breaks global FIFO.
    return mpmc_push(&q->mpmc, item);
}

bool ull_queue_pop(ull_queue_t *q, void **item) {
    if (!q) return false;
    return q->mode == 1 ? spsc_pop(&q->spsc, item) : mpmc_pop(&q->mpmc, item);
}

void ull_queue_set_mode(ull_queue_t *q, int mode) {
    if (!q) return;
    if (mode >= 0 && mode <= 2 && spsc_is_empty(&q->spsc) && mpmc_is_empty(&q->mpmc)) q->mode = mode;
}

size_t queue_storage_size(unsigned topology) {
    switch(topology) {
        case 0: return sizeof(spsc_queue_t);
        case 1: return sizeof(mpsc_queue_t);
        case 2: return sizeof(mpmc_queue_t);
        case 3: return sizeof(spmc_queue_t);
        case 4: return sizeof(ull_queue_t);
        case 5: return sizeof(disruptor_t);
        default: return 0;
    }
}
