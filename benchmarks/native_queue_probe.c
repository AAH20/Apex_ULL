/* SPDX-License-Identifier: AGPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "../kernels/queue/queue.h"
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <assert.h>
static uint64_t now(void) {
    struct timespec t;
    assert(clock_gettime(CLOCK_MONOTONIC, &t) == 0);
    return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
}
int main(int argc, char **argv) {
    if (argc != 4) return 2;
    size_t count = (size_t)strtoull(argv[1], NULL, 10);
    size_t warmup = (size_t)strtoull(argv[2], NULL, 10);
    size_t batch = (size_t)strtoull(argv[3], NULL, 10);
    if (!batch || batch > 65536) return 2;
    if (!count || count > 10000000 || warmup > 10000000) return 2;
    spsc_queue_t q;
    if (spsc_init(&q, 1024)) return 2;
    uint64_t *samples = calloc(count, sizeof(*samples));
    if (!samples) return 2;
    unsigned value = 42; void *out;
    for (size_t i = 0; i < warmup; ++i) {
        for (size_t j = 0; j < batch; ++j) {
            assert(spsc_push(&q, &value)); assert(spsc_pop(&q, &out)); assert(out == &value);
        }
    }
    const uint64_t start = now();
    for (size_t i = 0; i < count; ++i) {
        uint64_t t = now();
        for (size_t j = 0; j < batch; ++j) {
            assert(spsc_push(&q, &value)); assert(spsc_pop(&q, &out)); assert(out == &value);
        }
        samples[i] = now() - t;
    }
    const uint64_t elapsed = now() - start;
    struct timespec resolution;
    assert(clock_getres(CLOCK_MONOTONIC, &resolution) == 0);
    printf("{\"elapsed_ns\":%" PRIu64 ",\"clock_resolution_ns\":%" PRIu64 ",\"samples\":[", elapsed,
        (uint64_t)resolution.tv_sec * 1000000000ULL + (uint64_t)resolution.tv_nsec);
    for (size_t i = 0; i < count; ++i) printf("%s%" PRIu64, i ? "," : "", samples[i]);
    puts("]}");
    free(samples); spsc_destroy(&q); return 0;
}
