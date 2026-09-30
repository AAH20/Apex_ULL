/*
 * ULL Queue Optimization Kernel — C Header
 * =========================================
 * Bounded atomic queue implementations for HFT research and
 * real-time systems. All queues use cache-line alignment, power-of-2
 * ring sizes, and minimal memory barriers.
 *
 * Supported topologies:
 *   - SPSC: Single Producer, Single Consumer (zero CAS on fast path)
 *   - MPSC: Multi Producer, Single Consumer  (CAS on enqueue only)
 *   - MPMC: Multi Producer, Multi Consumer  (CAS on both ends)
 *   - SPMC: Single Producer, Multi Consumer  (CAS on dequeue only)
 *   - Disruptor: unavailable; init fails until a real sequence barrier exists
 *
 * Build:  clang -O3 -march=native -shared -fPIC -o libqueue.so queue.c
 */

#ifndef ULL_QUEUE_H
#define ULL_QUEUE_H

#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Cache line size (x86_64 and Apple Silicon) */
#define CACHE_LINE_SIZE 64

/* Align a value up to the next multiple of CACHE_LINE_SIZE */
#define CACHE_ALIGN(x) (((x) + CACHE_LINE_SIZE - 1) & ~(CACHE_LINE_SIZE - 1))

/* Power-of-2 ring size requirement */
#define QUEUE_MIN_SIZE 16
#define QUEUE_MAX_SIZE (1UL << 30)

/* ------------------------------------------------------------------ */
/* SPSC Ring Buffer                                                    */
/* ------------------------------------------------------------------ */

typedef struct {
    /* Producer-owned fields (written only by producer) */
    _Atomic uint64_t head __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad1[7];  /* pad to 64 bytes */

    /* Consumer-owned fields (written only by consumer) */
    _Atomic uint64_t tail __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad2[7];  /* pad to 64 bytes */

    /* Shared read-only fields */
    uint64_t mask;
    uint64_t capacity;
    void **ring;
} spsc_queue_t;

size_t queue_storage_size(unsigned topology);

int  spsc_init(spsc_queue_t *q, uint64_t capacity);
void spsc_destroy(spsc_queue_t *q);
bool spsc_push(spsc_queue_t *q, void *item);
bool spsc_pop(spsc_queue_t *q, void **item);
bool spsc_is_empty(const spsc_queue_t *q);
bool spsc_is_full(const spsc_queue_t *q);
uint64_t spsc_size(const spsc_queue_t *q);

/* Batch operations */
uint64_t spsc_push_batch(spsc_queue_t *q, void **items, uint64_t n);
uint64_t spsc_pop_batch(spsc_queue_t *q, void **items, uint64_t n);

/* ------------------------------------------------------------------ */
/* MPSC Ring Buffer                                                    */
/* ------------------------------------------------------------------ */

typedef struct {
    /* Producer side: CAS on head */
    _Atomic uint64_t head __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad1[7];

    /* Consumer side: written only by consumer */
    _Atomic uint64_t tail __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad2[7];

    uint64_t mask;
    uint64_t capacity;
    void **ring;
    _Atomic uint64_t *sequence; // Per-slot publication and reclamation.
} mpsc_queue_t;

int  mpsc_init(mpsc_queue_t *q, uint64_t capacity);
void mpsc_destroy(mpsc_queue_t *q);
bool mpsc_push(mpsc_queue_t *q, void *item);
bool mpsc_pop(mpsc_queue_t *q, void **item);
bool mpsc_is_empty(const mpsc_queue_t *q);
uint64_t mpsc_size(const mpsc_queue_t *q);

/* ------------------------------------------------------------------ */
/* MPMC Ring Buffer                                                    */
/* ------------------------------------------------------------------ */

typedef struct {
    _Atomic uint64_t head __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad1[7];

    _Atomic uint64_t tail __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad2[7];

    uint64_t mask;
    uint64_t capacity;
    void **ring;
    _Atomic uint64_t *sequence; // Per-slot publication and reclamation.
} mpmc_queue_t;

int  mpmc_init(mpmc_queue_t *q, uint64_t capacity);
void mpmc_destroy(mpmc_queue_t *q);
bool mpmc_push(mpmc_queue_t *q, void *item);
bool mpmc_pop(mpmc_queue_t *q, void **item);
bool mpmc_is_empty(const mpmc_queue_t *q);
uint64_t mpmc_size(const mpmc_queue_t *q);

/* ------------------------------------------------------------------ */
/* SPMC Ring Buffer                                                    */
/* ------------------------------------------------------------------ */

typedef struct {
    /* Producer side: written only by producer */
    _Atomic uint64_t head __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad1[7];

    /* Consumer side: CAS on tail */
    _Atomic uint64_t tail __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad2[7];

    uint64_t mask;
    uint64_t capacity;
    void **ring;
    _Atomic uint64_t *sequence; // Per-slot publication and reclamation.
} spmc_queue_t;

int  spmc_init(spmc_queue_t *q, uint64_t capacity);
void spmc_destroy(spmc_queue_t *q);
bool spmc_push(spmc_queue_t *q, void *item);
bool spmc_pop(spmc_queue_t *q, void **item);
bool spmc_is_empty(const spmc_queue_t *q);
uint64_t spmc_size(const spmc_queue_t *q);

/* ------------------------------------------------------------------ */
/* LMAX Disruptor                                                      */
/* ------------------------------------------------------------------ */

#define DISRUPTOR_MAX_CONSUMERS 16

typedef void (*disruptor_event_handler_t)(void *event, uint64_t sequence, void *ctx);

typedef struct {
    _Atomic uint64_t cursor __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad1[7];

    /* Consumer tracking */
    _Atomic uint64_t consumer_seq[DISRUPTOR_MAX_CONSUMERS] __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad2[7];

    /* Ring buffer */
    uint64_t mask;
    uint64_t capacity;
    void **ring;

    /* Consumer registry */
    disruptor_event_handler_t handlers[DISRUPTOR_MAX_CONSUMERS];
    void *handler_ctx[DISRUPTOR_MAX_CONSUMERS];
    uint32_t num_consumers;
} disruptor_t;

int  disruptor_init(disruptor_t *d, uint64_t capacity);
void disruptor_destroy(disruptor_t *d);
bool disruptor_register_consumer(disruptor_t *d, uint32_t id,
                                  disruptor_event_handler_t handler, void *ctx);
bool disruptor_publish(disruptor_t *d, void *event);
uint64_t disruptor_next_sequence(disruptor_t *d);
bool disruptor_claim(disruptor_t *d, uint64_t *seq);
void disruptor_commit(disruptor_t *d, uint64_t seq);

/* ------------------------------------------------------------------ */
/* Custom ULL Queue (hybrid: SPSC fast path + MPMC fallback)           */
/* ------------------------------------------------------------------ */

typedef struct {
    /* Fast path: SPSC ring for single-producer scenarios */
    spsc_queue_t spsc __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad1[7];

    /* Slow path: MPMC ring for multi-producer scenarios */
    mpmc_queue_t mpmc __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad2[7];

    /* Mode: 0/2 = MPMC, 1 = SPSC. Change only when quiescent and empty. */
    int mode;
    _Atomic uint64_t use_count;
} ull_queue_t;

int  ull_queue_init(ull_queue_t *q, uint64_t capacity);
void ull_queue_destroy(ull_queue_t *q);
bool ull_queue_push(ull_queue_t *q, void *item);
bool ull_queue_pop(ull_queue_t *q, void **item);
void ull_queue_set_mode(ull_queue_t *q, int mode);

/* ------------------------------------------------------------------ */
/* Utility: high-resolution timer (nanoseconds)                        */
/* ------------------------------------------------------------------ */

static inline uint64_t ull_now_ns(void) {
#if defined(__APPLE__)
    /* mach_absolute_time */
    extern uint64_t ull_mach_now(void);
    return ull_mach_now();
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
#endif
}

/* CPU pause / yield hint */
static inline void ull_cpu_pause(void) {
#if defined(__x86_64__) || defined(__i386__)
    __builtin_ia32_pause();
#elif defined(__aarch64__)
    __asm__ volatile("yield" ::: "memory");
#else
    __asm__ volatile("" ::: "memory");
#endif
}

/* Compiler memory barrier */
#define ull_compiler_barrier() __asm__ volatile("" ::: "memory")

/* Full memory barrier */
#define ull_memory_barrier() __atomic_thread_fence(__ATOMIC_SEQ_CST)

/* Acquire barrier */
#define ull_acquire_barrier() __atomic_thread_fence(__ATOMIC_ACQUIRE)

/* Release barrier */
#define ull_release_barrier() __atomic_thread_fence(__ATOMIC_RELEASE)

#ifdef __cplusplus
}
#endif

#endif /* ULL_QUEUE_H */
