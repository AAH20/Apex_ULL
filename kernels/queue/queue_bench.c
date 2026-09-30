/*
 * ULL Queue C-Level Benchmark
 * ============================
 * Pure C benchmark measuring true hardware-level queue performance
 * without Python ctypes overhead.
 *
 * Build:  clang -O3 -march=native -o queue_bench queue_bench.c queue.c
 * Run:    ./queue_bench [iterations]
 */

#include "queue.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define DEFAULT_ITERS 1000000
#define WARMUP_ITERS 10000
#define CAPACITY 4096

/* ================================================================== */
/* Stats helpers                                                       */
/* ================================================================== */

typedef struct {
    uint64_t min, max, sum, sum_sq;
    uint64_t *samples;
    uint64_t n;
    uint64_t cap;
} stats_t;

static void stats_init(stats_t *s, uint64_t cap) {
    s->min = UINT64_MAX;
    s->max = 0;
    s->sum = 0;
    s->sum_sq = 0;
    s->n = 0;
    s->cap = cap;
    s->samples = (uint64_t *)malloc(cap * sizeof(uint64_t));
}

static void stats_free(stats_t *s) {
    free(s->samples);
}

static void stats_add(stats_t *s, uint64_t val) {
    if (val < s->min) s->min = val;
    if (val > s->max) s->max = val;
    s->sum += val;
    s->sum_sq += (unsigned __int128)val * val;
    if (s->n < s->cap) s->samples[s->n] = val;
    s->n++;
}

static int cmp_u64(const void *a, const void *b) {
    uint64_t ua = *(const uint64_t *)a;
    uint64_t ub = *(const uint64_t *)b;
    return (ua > ub) - (ua < ub);
}

static uint64_t stats_percentile(stats_t *s, double p) {
    if (s->n == 0) return 0;
    uint64_t *tmp = (uint64_t *)malloc(s->n * sizeof(uint64_t));
    memcpy(tmp, s->samples, s->n * sizeof(uint64_t));
    qsort(tmp, s->n, sizeof(uint64_t), cmp_u64);
    uint64_t idx = (uint64_t)(p * (s->n - 1));
    uint64_t val = tmp[idx];
    free(tmp);
    return val;
}

static double stats_mean(stats_t *s) {
    return s->n > 0 ? (double)s->sum / s->n : 0;
}

static double stats_stdev(stats_t *s) {
    if (s->n < 2) return 0;
    double m = stats_mean(s);
    double var = (double)((unsigned __int128)s->sum_sq / s->n) - m * m;
    return sqrt(var > 0 ? var : 0);
}

/* ================================================================== */
/* Benchmarks                                                          */
/* ================================================================== */

static void bench_spsc(uint64_t iters) {
    spsc_queue_t q;
    spsc_init(&q, CAPACITY);
    stats_t push_st, pop_st;
    stats_init(&push_st, iters);
    stats_init(&pop_st, iters);

    /* Warmup */
    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        spsc_push(&q, (void *)(i + 1));
        void *item;
        spsc_pop(&q, &item);
    }

    for (uint64_t i = 0; i < iters; i++) {
        uint64_t t0 = ull_now_ns();
        spsc_push(&q, (void *)(i + 1));
        uint64_t t1 = ull_now_ns();
        void *item;
        spsc_pop(&q, &item);
        uint64_t t2 = ull_now_ns();
        stats_add(&push_st, t1 - t0);
        stats_add(&pop_st, t2 - t1);
    }

    printf("SPSC  push: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&push_st, 0.50),
           stats_percentile(&push_st, 0.99),
           stats_percentile(&push_st, 0.999),
           push_st.max, stats_mean(&push_st));
    printf("SPSC  pop:  p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&pop_st, 0.50),
           stats_percentile(&pop_st, 0.99),
           stats_percentile(&pop_st, 0.999),
           pop_st.max, stats_mean(&pop_st));

    stats_free(&push_st);
    stats_free(&pop_st);
    spsc_destroy(&q);
}

static void bench_mpsc(uint64_t iters) {
    mpsc_queue_t q;
    mpsc_init(&q, CAPACITY);
    stats_t push_st, pop_st;
    stats_init(&push_st, iters);
    stats_init(&pop_st, iters);

    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        mpsc_push(&q, (void *)(i + 1));
        void *item;
        mpsc_pop(&q, &item);
    }

    for (uint64_t i = 0; i < iters; i++) {
        uint64_t t0 = ull_now_ns();
        mpsc_push(&q, (void *)(i + 1));
        uint64_t t1 = ull_now_ns();
        void *item;
        mpsc_pop(&q, &item);
        uint64_t t2 = ull_now_ns();
        stats_add(&push_st, t1 - t0);
        stats_add(&pop_st, t2 - t1);
    }

    printf("MPSC  push: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&push_st, 0.50),
           stats_percentile(&push_st, 0.99),
           stats_percentile(&push_st, 0.999),
           push_st.max, stats_mean(&push_st));
    printf("MPSC  pop:  p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&pop_st, 0.50),
           stats_percentile(&pop_st, 0.99),
           stats_percentile(&pop_st, 0.999),
           pop_st.max, stats_mean(&pop_st));

    stats_free(&push_st);
    stats_free(&pop_st);
    mpsc_destroy(&q);
}

static void bench_mpmc(uint64_t iters) {
    mpmc_queue_t q;
    mpmc_init(&q, CAPACITY);
    stats_t push_st, pop_st;
    stats_init(&push_st, iters);
    stats_init(&pop_st, iters);

    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        mpmc_push(&q, (void *)(i + 1));
        void *item;
        mpmc_pop(&q, &item);
    }

    for (uint64_t i = 0; i < iters; i++) {
        uint64_t t0 = ull_now_ns();
        mpmc_push(&q, (void *)(i + 1));
        uint64_t t1 = ull_now_ns();
        void *item;
        mpmc_pop(&q, &item);
        uint64_t t2 = ull_now_ns();
        stats_add(&push_st, t1 - t0);
        stats_add(&pop_st, t2 - t1);
    }

    printf("MPMC  push: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&push_st, 0.50),
           stats_percentile(&push_st, 0.99),
           stats_percentile(&push_st, 0.999),
           push_st.max, stats_mean(&push_st));
    printf("MPMC  pop:  p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&pop_st, 0.50),
           stats_percentile(&pop_st, 0.99),
           stats_percentile(&pop_st, 0.999),
           pop_st.max, stats_mean(&pop_st));

    stats_free(&push_st);
    stats_free(&pop_st);
    mpmc_destroy(&q);
}

static void bench_spmc(uint64_t iters) {
    spmc_queue_t q;
    spmc_init(&q, CAPACITY);
    stats_t push_st, pop_st;
    stats_init(&push_st, iters);
    stats_init(&pop_st, iters);

    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        spmc_push(&q, (void *)(i + 1));
        void *item;
        spmc_pop(&q, &item);
    }

    for (uint64_t i = 0; i < iters; i++) {
        uint64_t t0 = ull_now_ns();
        spmc_push(&q, (void *)(i + 1));
        uint64_t t1 = ull_now_ns();
        void *item;
        spmc_pop(&q, &item);
        uint64_t t2 = ull_now_ns();
        stats_add(&push_st, t1 - t0);
        stats_add(&pop_st, t2 - t1);
    }

    printf("SPMC  push: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&push_st, 0.50),
           stats_percentile(&push_st, 0.99),
           stats_percentile(&push_st, 0.999),
           push_st.max, stats_mean(&push_st));
    printf("SPMC  pop:  p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&pop_st, 0.50),
           stats_percentile(&pop_st, 0.99),
           stats_percentile(&pop_st, 0.999),
           pop_st.max, stats_mean(&pop_st));

    stats_free(&push_st);
    stats_free(&pop_st);
    spmc_destroy(&q);
}

static void bench_disruptor(uint64_t iters) {
    disruptor_t d;
    disruptor_init(&d, CAPACITY);
    stats_t pub_st;
    stats_init(&pub_st, iters);

    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        disruptor_publish(&d, (void *)(i + 1));
    }

    for (uint64_t i = 0; i < iters; i++) {
        uint64_t t0 = ull_now_ns();
        disruptor_publish(&d, (void *)(i + 1));
        uint64_t t1 = ull_now_ns();
        stats_add(&pub_st, t1 - t0);
    }

    printf("Disruptor publish: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&pub_st, 0.50),
           stats_percentile(&pub_st, 0.99),
           stats_percentile(&pub_st, 0.999),
           pub_st.max, stats_mean(&pub_st));

    stats_free(&pub_st);
    disruptor_destroy(&d);
}

static void bench_throughput(uint64_t iters) {
    /* SPSC throughput */
    {
        spsc_queue_t q;
        spsc_init(&q, CAPACITY);
        for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
            spsc_push(&q, (void *)(i + 1));
            void *item;
            spsc_pop(&q, &item);
        }
        uint64_t t0 = ull_now_ns();
        for (uint64_t i = 0; i < iters; i++) {
            spsc_push(&q, (void *)(i + 1));
            void *item;
            spsc_pop(&q, &item);
        }
        uint64_t t1 = ull_now_ns();
        double elapsed_s = (double)(t1 - t0) / 1e9;
        printf("SPSC throughput: %.1fM ops/s\n", (double)iters * 2 / elapsed_s / 1e6);
        spsc_destroy(&q);
    }

    /* MPMC throughput */
    {
        mpmc_queue_t q;
        mpmc_init(&q, CAPACITY);
        for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
            mpmc_push(&q, (void *)(i + 1));
            void *item;
            mpmc_pop(&q, &item);
        }
        uint64_t t0 = ull_now_ns();
        for (uint64_t i = 0; i < iters; i++) {
            mpmc_push(&q, (void *)(i + 1));
            void *item;
            mpmc_pop(&q, &item);
        }
        uint64_t t1 = ull_now_ns();
        double elapsed_s = (double)(t1 - t0) / 1e9;
        printf("MPMC throughput: %.1fM ops/s\n", (double)iters * 2 / elapsed_s / 1e6);
        mpmc_destroy(&q);
    }

    /* Disruptor throughput */
    {
        disruptor_t d;
        disruptor_init(&d, CAPACITY);
        for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
            disruptor_publish(&d, (void *)(i + 1));
        }
        uint64_t t0 = ull_now_ns();
        for (uint64_t i = 0; i < iters; i++) {
            disruptor_publish(&d, (void *)(i + 1));
        }
        uint64_t t1 = ull_now_ns();
        double elapsed_s = (double)(t1 - t0) / 1e9;
        printf("Disruptor throughput: %.1fM ops/s\n", (double)iters / elapsed_s / 1e6);
        disruptor_destroy(&d);
    }
}

/* ================================================================== */
/* Main                                                                */
/* ================================================================== */

int main(int argc, char **argv) {
    uint64_t iters = DEFAULT_ITERS;
    if (argc > 1) {
        iters = strtoull(argv[1], NULL, 10);
    }

    printf("ULL Queue C-Level Benchmark\n");
    printf("============================\n");
    printf("Iterations: %llu\n", iters);
    printf("Capacity: %d\n", CAPACITY);
    printf("Warmup: %d\n\n", WARMUP_ITERS);

    printf("--- Latency (ns) ---\n");
    bench_spsc(iters);
    bench_mpsc(iters);
    bench_mpmc(iters);
    bench_spmc(iters);
    bench_disruptor(iters);

    printf("\n--- Throughput ---\n");
    bench_throughput(iters);

    return 0;
}
