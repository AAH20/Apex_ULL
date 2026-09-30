/*
 * ULL Network Stack — C-Level Benchmark
 * =====================================
 * Pure C benchmark measuring true hardware-level network stack performance
 * without Python ctypes overhead.
 *
 * Build:  clang -O3 -march=native -o net_stack_bench net_stack_bench.c net_stack.c
 * Run:    ./net_stack_bench [iterations]
 */

#include "net_stack.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define DEFAULT_ITERS 1000000
#define WARMUP_ITERS 10000
#define RING_CAPACITY 4096
#define POOL_CAPACITY 65536
#define BUF_SIZE 9000

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
/* Ring buffer benchmarks                                              */
/* ================================================================== */

static void bench_ring_push_pop(uint64_t iters) {
    net_ring_t ring;
    net_ring_init(&ring, RING_CAPACITY);
    stats_t push_st, pop_st;
    stats_init(&push_st, iters);
    stats_init(&pop_st, iters);

    /* Warmup */
    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        net_buf_t *buf = (net_buf_t *)(i + 1);
        net_ring_push(&ring, buf);
        net_buf_t *out;
        net_ring_pop(&ring, &out);
    }

    for (uint64_t i = 0; i < iters; i++) {
        uint64_t t0 = net_now_ns();
        net_buf_t *buf = (net_buf_t *)(i + 1);
        net_ring_push(&ring, buf);
        uint64_t t1 = net_now_ns();
        net_buf_t *out;
        net_ring_pop(&ring, &out);
        uint64_t t2 = net_now_ns();
        stats_add(&push_st, t1 - t0);
        stats_add(&pop_st, t2 - t1);
    }

    printf("Ring push: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&push_st, 0.50),
           stats_percentile(&push_st, 0.99),
           stats_percentile(&push_st, 0.999),
           push_st.max, stats_mean(&push_st));
    printf("Ring pop:  p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&pop_st, 0.50),
           stats_percentile(&pop_st, 0.99),
           stats_percentile(&pop_st, 0.999),
           pop_st.max, stats_mean(&pop_st));

    stats_free(&push_st);
    stats_free(&pop_st);
    net_ring_destroy(&ring);
}

static void bench_ring_batch(uint64_t iters) {
    net_ring_t ring;
    net_ring_init(&ring, RING_CAPACITY);
    stats_t push_st, pop_st;
    stats_init(&push_st, iters / 32);
    stats_init(&pop_st, iters / 32);

    net_buf_t *bufs[32];
    net_buf_t *out[32];

    /* Warmup */
    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        for (int j = 0; j < 32; j++) bufs[j] = (net_buf_t *)(i * 32 + j + 1);
        net_ring_push_batch(&ring, bufs, 32);
        net_ring_pop_batch(&ring, out, 32);
    }

    for (uint64_t i = 0; i < iters / 32; i++) {
        for (int j = 0; j < 32; j++) bufs[j] = (net_buf_t *)(i * 32 + j + 1);
        uint64_t t0 = net_now_ns();
        net_ring_push_batch(&ring, bufs, 32);
        uint64_t t1 = net_now_ns();
        net_ring_pop_batch(&ring, out, 32);
        uint64_t t2 = net_now_ns();
        stats_add(&push_st, t1 - t0);
        stats_add(&pop_st, t2 - t1);
    }

    printf("Ring batch push (32): p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&push_st, 0.50),
           stats_percentile(&push_st, 0.99),
           stats_percentile(&push_st, 0.999),
           push_st.max, stats_mean(&push_st));
    printf("Ring batch pop (32):  p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&pop_st, 0.50),
           stats_percentile(&pop_st, 0.99),
           stats_percentile(&pop_st, 0.999),
           pop_st.max, stats_mean(&pop_st));

    stats_free(&push_st);
    stats_free(&pop_st);
    net_ring_destroy(&ring);
}

/* ================================================================== */
/* Buffer pool benchmarks                                              */
/* ================================================================== */

static void bench_buf_pool(uint64_t iters) {
    net_buf_pool_t pool;
    net_buf_pool_init(&pool, POOL_CAPACITY, BUF_SIZE);
    stats_t alloc_st, free_st;
    stats_init(&alloc_st, iters);
    stats_init(&free_st, iters);

    /* Warmup */
    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        net_buf_t *buf = net_buf_alloc(&pool);
        net_buf_free(&pool, buf);
    }

    for (uint64_t i = 0; i < iters; i++) {
        uint64_t t0 = net_now_ns();
        net_buf_t *buf = net_buf_alloc(&pool);
        uint64_t t1 = net_now_ns();
        net_buf_free(&pool, buf);
        uint64_t t2 = net_now_ns();
        stats_add(&alloc_st, t1 - t0);
        stats_add(&free_st, t2 - t1);
    }

    printf("Buf alloc: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&alloc_st, 0.50),
           stats_percentile(&alloc_st, 0.99),
           stats_percentile(&alloc_st, 0.999),
           alloc_st.max, stats_mean(&alloc_st));
    printf("Buf free:  p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&free_st, 0.50),
           stats_percentile(&free_st, 0.99),
           stats_percentile(&free_st, 0.999),
           free_st.max, stats_mean(&free_st));

    stats_free(&alloc_st);
    stats_free(&free_st);
    net_buf_pool_destroy(&pool);
}

/* ================================================================== */
/* Completion queue benchmarks                                         */
/* ================================================================== */

static void bench_cq(uint64_t iters) {
    net_cq_t cq;
    net_cq_init(&cq, RING_CAPACITY);
    stats_t push_st, pop_st;
    stats_init(&push_st, iters);
    stats_init(&pop_st, iters);

    /* Warmup */
    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        net_cqe_t cqe = { (net_buf_t *)(i + 1), NET_CQ_OK, 64, i };
        net_cq_push(&cq, &cqe);
        net_cqe_t out;
        net_cq_pop(&cq, &out);
    }

    for (uint64_t i = 0; i < iters; i++) {
        net_cqe_t cqe = { (net_buf_t *)(i + 1), NET_CQ_OK, 64, i };
        uint64_t t0 = net_now_ns();
        net_cq_push(&cq, &cqe);
        uint64_t t1 = net_now_ns();
        net_cqe_t out;
        net_cq_pop(&cq, &out);
        uint64_t t2 = net_now_ns();
        stats_add(&push_st, t1 - t0);
        stats_add(&pop_st, t2 - t1);
    }

    printf("CQ push: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&push_st, 0.50),
           stats_percentile(&push_st, 0.99),
           stats_percentile(&push_st, 0.999),
           push_st.max, stats_mean(&push_st));
    printf("CQ pop:  p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&pop_st, 0.50),
           stats_percentile(&pop_st, 0.99),
           stats_percentile(&pop_st, 0.999),
           pop_st.max, stats_mean(&pop_st));

    stats_free(&push_st);
    stats_free(&pop_st);
    net_cq_destroy(&cq);
}

/* ================================================================== */
/* Queue pair benchmarks                                               */
/* ================================================================== */

static void bench_qp(uint64_t iters) {
    net_buf_pool_t pool;
    net_buf_pool_init(&pool, POOL_CAPACITY, BUF_SIZE);

    net_qp_t qp;
    net_qp_init(&qp, 1, &pool, RING_CAPACITY);

    stats_t send_st, recv_st;
    stats_init(&send_st, iters);
    stats_init(&recv_st, iters);

    /* Warmup */
    for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
        net_buf_t *buf = net_buf_alloc(&pool);
        net_qp_send(&qp, buf);
        net_qp_loopback(&qp);
        net_buf_t *out;
        net_qp_recv(&qp, &out);
        net_buf_free(&pool, out);
    }

    for (uint64_t i = 0; i < iters; i++) {
        net_buf_t *buf = net_buf_alloc(&pool);
        uint64_t t0 = net_now_ns();
        net_qp_send(&qp, buf);
        uint64_t t1 = net_now_ns();
        net_qp_loopback(&qp);
        net_buf_t *out;
        net_qp_recv(&qp, &out);
        uint64_t t2 = net_now_ns();
        net_buf_free(&pool, out);
        stats_add(&send_st, t1 - t0);
        stats_add(&recv_st, t2 - t1);
    }

    printf("QP send: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&send_st, 0.50),
           stats_percentile(&send_st, 0.99),
           stats_percentile(&send_st, 0.999),
           send_st.max, stats_mean(&send_st));
    printf("QP recv: p50=%llu p99=%llu p99.9=%llu max=%llu mean=%.1f\n",
           stats_percentile(&recv_st, 0.50),
           stats_percentile(&recv_st, 0.99),
           stats_percentile(&recv_st, 0.999),
           recv_st.max, stats_mean(&recv_st));

    stats_free(&send_st);
    stats_free(&recv_st);
    net_qp_destroy(&qp);
    net_buf_pool_destroy(&pool);
}

/* ================================================================== */
/* Throughput benchmarks                                               */
/* ================================================================== */

static void bench_throughput(uint64_t iters) {
    /* Ring throughput */
    {
        net_ring_t ring;
        net_ring_init(&ring, RING_CAPACITY);
        for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
            net_buf_t *buf = (net_buf_t *)(i + 1);
            net_ring_push(&ring, buf);
            net_buf_t *out;
            net_ring_pop(&ring, &out);
        }
        uint64_t t0 = net_now_ns();
        for (uint64_t i = 0; i < iters; i++) {
            net_buf_t *buf = (net_buf_t *)(i + 1);
            net_ring_push(&ring, buf);
            net_buf_t *out;
            net_ring_pop(&ring, &out);
        }
        uint64_t t1 = net_now_ns();
        double elapsed_s = (double)(t1 - t0) / 1e9;
        printf("Ring throughput: %.1fM ops/s\n", (double)iters * 2 / elapsed_s / 1e6);
        net_ring_destroy(&ring);
    }

    /* Buffer pool throughput */
    {
        net_buf_pool_t pool;
        net_buf_pool_init(&pool, POOL_CAPACITY, BUF_SIZE);
        for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
            net_buf_t *buf = net_buf_alloc(&pool);
            net_buf_free(&pool, buf);
        }
        uint64_t t0 = net_now_ns();
        for (uint64_t i = 0; i < iters; i++) {
            net_buf_t *buf = net_buf_alloc(&pool);
            net_buf_free(&pool, buf);
        }
        uint64_t t1 = net_now_ns();
        double elapsed_s = (double)(t1 - t0) / 1e9;
        printf("Buf pool throughput: %.1fM ops/s\n", (double)iters * 2 / elapsed_s / 1e6);
        net_buf_pool_destroy(&pool);
    }

    /* QP throughput */
    {
        net_buf_pool_t pool;
        net_buf_pool_init(&pool, POOL_CAPACITY, BUF_SIZE);
        net_qp_t qp;
        net_qp_init(&qp, 1, &pool, RING_CAPACITY);
        for (uint64_t i = 0; i < WARMUP_ITERS; i++) {
            net_buf_t *buf = net_buf_alloc(&pool);
            net_qp_send(&qp, buf);
            net_qp_loopback(&qp);
            net_buf_t *out;
            net_qp_recv(&qp, &out);
            net_buf_free(&pool, out);
        }
        uint64_t t0 = net_now_ns();
        for (uint64_t i = 0; i < iters; i++) {
            net_buf_t *buf = net_buf_alloc(&pool);
            net_qp_send(&qp, buf);
            net_qp_loopback(&qp);
            net_buf_t *out;
            net_qp_recv(&qp, &out);
            net_buf_free(&pool, out);
        }
        uint64_t t1 = net_now_ns();
        double elapsed_s = (double)(t1 - t0) / 1e9;
        printf("QP throughput: %.1fM ops/s\n", (double)iters * 3 / elapsed_s / 1e6);
        net_qp_destroy(&qp);
        net_buf_pool_destroy(&pool);
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

    printf("ULL Network Stack C-Level Benchmark\n");
    printf("====================================\n");
    printf("Iterations: %llu\n", iters);
    printf("Ring capacity: %d\n", RING_CAPACITY);
    printf("Pool capacity: %d\n", POOL_CAPACITY);
    printf("Buffer size: %d\n", BUF_SIZE);
    printf("Warmup: %d\n\n", WARMUP_ITERS);

    printf("--- Ring Buffer Latency (ns) ---\n");
    bench_ring_push_pop(iters);

    printf("\n--- Ring Batch Latency (ns) ---\n");
    bench_ring_batch(iters);

    printf("\n--- Buffer Pool Latency (ns) ---\n");
    bench_buf_pool(iters);

    printf("\n--- Completion Queue Latency (ns) ---\n");
    bench_cq(iters);

    printf("\n--- Queue Pair Latency (ns) ---\n");
    bench_qp(iters);

    printf("\n--- Throughput ---\n");
    bench_throughput(iters);

    return 0;
}
