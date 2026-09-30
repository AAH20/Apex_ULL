/*
 * ULL Ring Buffer — C Implementation
 * ====================================
 * Fixed-capacity SPSC ring buffer with cache-line alignment.
 *
 * Build: clang -O3 -march=native -shared -fPIC -o libring_buffer.so ring_buffer.c
 */

#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define CACHE_LINE_SIZE 64

typedef struct {
    _Atomic uint64_t head __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad1[7];

    _Atomic uint64_t tail __attribute__((aligned(CACHE_LINE_SIZE)));
    uint64_t _pad2[7];

    uint64_t mask;
    uint64_t capacity;
    void **ring;
} ring_buffer_t;

int ring_init(ring_buffer_t *rb, uint64_t capacity) {
    rb->head = 0;
    rb->tail = 0;
    rb->mask = capacity - 1;
    rb->capacity = capacity;
    rb->ring = (void **)calloc(capacity, sizeof(void *));
    return rb->ring ? 0 : -1;
}

void ring_destroy(ring_buffer_t *rb) {
    free(rb->ring);
    rb->ring = NULL;
}

bool ring_push(ring_buffer_t *rb, void *item) {
    uint64_t head = atomic_load_explicit(&rb->head, memory_order_relaxed);
    uint64_t next_head = (head + 1) & rb->mask;

    if (next_head == atomic_load_explicit(&rb->tail, memory_order_acquire)) {
        return false;  /* full */
    }

    rb->ring[head] = item;
    atomic_store_explicit(&rb->head, next_head, memory_order_release);
    return true;
}

bool ring_pop(ring_buffer_t *rb, void **item) {
    uint64_t tail = atomic_load_explicit(&rb->tail, memory_order_relaxed);

    if (tail == atomic_load_explicit(&rb->head, memory_order_acquire)) {
        return false;  /* empty */
    }

    *item = rb->ring[tail];
    rb->ring[tail] = NULL;
    atomic_store_explicit(&rb->tail, (tail + 1) & rb->mask, memory_order_release);
    return true;
}

bool ring_is_empty(const ring_buffer_t *rb) {
    return atomic_load_explicit(&rb->head, memory_order_acquire) ==
           atomic_load_explicit(&rb->tail, memory_order_acquire);
}

bool ring_is_full(const ring_buffer_t *rb) {
    uint64_t head = atomic_load_explicit(&rb->head, memory_order_acquire);
    uint64_t tail = atomic_load_explicit(&rb->tail, memory_order_acquire);
    return ((head + 1) & rb->mask) == tail;
}

uint64_t ring_size(const ring_buffer_t *rb) {
    uint64_t head = atomic_load_explicit(&rb->head, memory_order_acquire);
    uint64_t tail = atomic_load_explicit(&rb->tail, memory_order_acquire);
    return (head - tail) & rb->mask;
}

uint64_t ring_push_batch(ring_buffer_t *rb, void **items, uint64_t n) {
    uint64_t head = atomic_load_explicit(&rb->head, memory_order_relaxed);
    uint64_t tail = atomic_load_explicit(&rb->tail, memory_order_acquire);
    uint64_t available = (tail - head - 1) & rb->mask;
    uint64_t count = (n < available) ? n : available;

    for (uint64_t i = 0; i < count; i++) {
        rb->ring[(head + i) & rb->mask] = items[i];
    }
    atomic_store_explicit(&rb->head, (head + count) & rb->mask, memory_order_release);
    return count;
}

uint64_t ring_pop_batch(ring_buffer_t *rb, void **items, uint64_t n) {
    uint64_t tail = atomic_load_explicit(&rb->tail, memory_order_relaxed);
    uint64_t head = atomic_load_explicit(&rb->head, memory_order_acquire);
    uint64_t available = (head - tail) & rb->mask;
    uint64_t count = (n < available) ? n : available;

    for (uint64_t i = 0; i < count; i++) {
        items[i] = rb->ring[(tail + i) & rb->mask];
        rb->ring[(tail + i) & rb->mask] = NULL;
    }
    atomic_store_explicit(&rb->tail, (tail + count) & rb->mask, memory_order_release);
    return count;
}
