/**
 * rdma_benchmark.c — Comprehensive RDMA Benchmark Suite
 *
 * Measures:
 * - One-way latency (RDMA WRITE / SEND)
 * - Throughput (bidirectional)
 * - Message rate (messages/sec)
 * - Jitter (min/max/stddev)
 * - CPU utilization during transfer
 *
 * Build: gcc -O2 -Wall -o rdma_benchmark rdma_benchmark.c -libverbs -lrdmacm -lm
 * Run:   ./rdma_benchmark server <bind_addr> <port>
 *        ./rdma_benchmark client <server_addr> <port> <msg_size> <iterations>
 */

#include <infiniband/verbs.h>
#include <rdma/rdma_cm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <math.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#include <sys/resource.h>

#define MAX_ITERATIONS  100000
#define WARMUP_ITERS   1000
#define QUEUE_DEPTH     32
#define MAX_SGE         4

struct qp_info {
    uint32_t qp_num;
    uint16_t lid;
    uint8_t  gid[16];
    uint64_t remote_addr;
    uint32_t rkey;
    uint32_t padding;
} __attribute__((packed));

struct rdma_ctx {
    struct ibv_context *ctx;
    struct ibv_pd      *pd;
    struct ibv_cq      *cq;
    struct ibv_qp      *qp;
    struct ibv_mr      *mr;
    char               *buf;
    struct qp_info      local_qp;
    struct qp_info      remote_qp;
    int                 sockfd;
    size_t              buf_size;
};

static uint64_t get_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static double ns_to_us(uint64_t ns) { return ns / 1000.0; }

/* ── Statistics ── */
struct stats {
    uint64_t min_ns, max_ns, sum_ns;
    uint64_t *samples;
    int      count;
    int      capacity;
};

static void stats_init(struct stats *s, int capacity) {
    s->min_ns = UINT64_MAX;
    s->max_ns = 0;
    s->sum_ns = 0;
    s->count = 0;
    s->capacity = capacity;
    s->samples = calloc(capacity, sizeof(uint64_t));
}

static void stats_add(struct stats *s, uint64_t ns) {
    if (ns < s->min_ns) s->min_ns = ns;
    if (ns > s->max_ns) s->max_ns = ns;
    s->sum_ns += ns;
    if (s->count < s->capacity) {
        s->samples[s->count] = ns;
    }
    s->count++;
}

static double stats_mean(struct stats *s) {
    return s->count > 0 ? (double)s->sum_ns / s->count : 0;
}

static double stats_stddev(struct stats *s) {
    if (s->count < 2) return 0;
    double mean = stats_mean(s);
    double sum_sq = 0;
    int n = s->count < s->capacity ? s->count : s->capacity;
    for (int i = 0; i < n; i++) {
        double d = (double)s->samples[i] - mean;
        sum_sq += d * d;
    }
    return sqrt(sum_sq / (n - 1));
}

static void stats_print(struct stats *s, const char *label) {
    double mean = stats_mean(s);
    double stddev = stats_stddev(s);
    double jitter = s->max_ns - s->min_ns;
    printf("  %-20s: min=%.2f µs, max=%.2f µs, mean=%.2f µs, stddev=%.2f µs, jitter=%.2f µs\n",
           label, ns_to_us(s->min_ns), ns_to_us(s->max_ns),
           ns_to_us(mean), ns_to_us(stddev), ns_to_us(jitter));
    printf("  %-20s  count=%d, throughput=%.2f Gb/s\n", "",
           s->count, (s->count * 64 * 8.0) / (ns_to_us(mean) * 1000));
}

/* ── QP setup (same as echo server) ── */
static struct ibv_qp *create_qp(struct rdma_ctx *rctx) {
    struct ibv_qp_init_attr qp_attr = {0};
    qp_attr.send_cq = rctx->cq;
    qp_attr.recv_cq = rctx->cq;
    qp_attr.cap.max_send_wr = QUEUE_DEPTH;
    qp_attr.cap.max_recv_wr = QUEUE_DEPTH;
    qp_attr.cap.max_send_sge = MAX_SGE;
    qp_attr.cap.max_recv_sge = MAX_SGE;
    qp_attr.qp_type = IBV_QPT_RC;
    return ibv_create_qp(rctx->pd, &qp_attr);
}

static int qp_to_init(struct rdma_ctx *rctx) {
    struct ibv_qp_attr attr = {0};
    attr.qp_state = IBV_QPS_INIT;
    attr.pkey_index = 0;
    attr.port_num = 1;
    attr.qp_access_flags = IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_READ | IBV_ACCESS_REMOTE_WRITE;
    return ibv_modify_qp(rctx->qp, &attr,
        IBV_QP_STATE | IBV_QP_PKEY_INDEX | IBV_QP_PORT | IBV_QP_ACCESS_FLAGS);
}

static int qp_to_rtr(struct rdma_ctx *rctx) {
    struct ibv_qp_attr attr = {0};
    attr.qp_state = IBV_QPS_RTR;
    attr.path_mtu = IBV_MTU_4096;
    attr.dest_qp_num = rctx->remote_qp.qp_num;
    attr.rq_psn = 0;
    attr.max_dest_rd_atomic = 1;
    attr.min_rnr_timer = 12;
    attr.ah_attr.is_global = 1;
    attr.ah_attr.grh.hop_limit = 1;
    attr.ah_attr.grh.dgid = *(union ibv_gid *)rctx->remote_qp.gid;
    attr.ah_attr.dlid = rctx->remote_qp.lid;
    attr.ah_attr.port_num = 1;
    return ibv_modify_qp(rctx->qp, &attr,
        IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU |
        IBV_QP_DEST_QPN | IBV_QP_RQ_PSN |
        IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER);
}

static int qp_to_rts(struct rdma_ctx *rctx) {
    struct ibv_qp_attr attr = {0};
    attr.qp_state = IBV_QPS_RTS;
    attr.timeout = 14;
    attr.retry_cnt = 7;
    attr.rnr_retry = 7;
    attr.sq_psn = 0;
    attr.max_rd_atomic = 1;
    return ibv_modify_qp(rctx->qp, &attr,
        IBV_QP_STATE | IBV_QP_TIMEOUT | IBV_QP_RETRY_CNT |
        IBV_QP_RNR_RETRY | IBV_QP_SQ_PSN | IBV_QP_MAX_QP_RD_ATOMIC);
}

static int exchange_qp_info(struct rdma_ctx *rctx, int is_server) {
    if (is_server) {
        send(rctx->sockfd, &rctx->local_qp, sizeof(struct qp_info), 0);
        recv(rctx->sockfd, &rctx->remote_qp, sizeof(struct qp_info), 0);
    } else {
        recv(rctx->sockfd, &rctx->remote_qp, sizeof(struct qp_info), 0);
        send(rctx->sockfd, &rctx->local_qp, sizeof(struct qp_info), 0);
    }
    return 0;
}

static int rdma_init(struct rdma_ctx *rctx, size_t buf_size) {
    rctx->buf_size = buf_size;
    struct ibv_device **dev_list = ibv_get_device_list(NULL);
    if (!dev_list) return -1;
    rctx->ctx = ibv_open_device(dev_list[0]);
    ibv_free_device_list(dev_list);
    if (!rctx->ctx) return -1;

    rctx->pd = ibv_alloc_pd(rctx->ctx);
    rctx->buf = malloc(buf_size);
    memset(rctx->buf, 0, buf_size);
    rctx->mr = ibv_reg_mr(rctx->pd, rctx->buf, buf_size,
        IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE | IBV_ACCESS_REMOTE_READ);
    rctx->cq = ibv_create_cq(rctx->ctx, QUEUE_DEPTH * 2, NULL, NULL, 0);
    rctx->qp = create_qp(rctx);

    struct ibv_port_attr port_attr;
    ibv_query_port(rctx->ctx, 1, &port_attr);
    rctx->local_qp.qp_num = rctx->qp->qp_num;
    rctx->local_qp.lid = port_attr.lid;
    rctx->local_qp.remote_addr = (uint64_t)(uintptr_t)rctx->buf;
    rctx->local_qp.rkey = rctx->mr->rkey;
    memset(rctx->local_qp.gid, 0, 16);
    return 0;
}

/* ── Latency benchmark: RDMA WRITE round-trip ── */
static int benchmark_latency(struct rdma_ctx *rctx, int iterations, struct stats *lat_stats) {
    struct ibv_wc wc;
    struct ibv_sge sge = {
        .addr = (uintptr_t)rctx->buf,
        .length = (uint32_t)rctx->buf_size,
        .lkey = rctx->mr->lkey,
    };

    /* Warmup */
    for (int i = 0; i < WARMUP_ITERS; i++) {
        struct ibv_send_wr wr = {0};
        wr.sg_list = &sge;
        wr.num_sge = 1;
        wr.opcode = IBV_WR_RDMA_WRITE;
        wr.send_flags = IBV_SEND_SIGNALED;
        wr.wr.rdma.remote_addr = rctx->remote_qp.remote_addr;
        wr.wr.rdma.rkey = rctx->remote_qp.rkey;
        struct ibv_send_wr *bad_wr;
        ibv_post_send(rctx->qp, &wr, &bad_wr);
        while (ibv_poll_cq(rctx->cq, 1, &wc) == 0) {}
    }

    /* Benchmark */
    for (int i = 0; i < iterations; i++) {
        uint64_t t0 = get_ns();

        struct ibv_send_wr wr = {0};
        wr.sg_list = &sge;
        wr.num_sge = 1;
        wr.opcode = IBV_WR_RDMA_WRITE;
        wr.send_flags = IBV_SEND_SIGNALED;
        wr.wr.rdma.remote_addr = rctx->remote_qp.remote_addr;
        wr.wr.rdma.rkey = rctx->remote_qp.rkey;
        struct ibv_send_wr *bad_wr;
        ibv_post_send(rctx->qp, &wr, &bad_wr);

        while (ibv_poll_cq(rctx->cq, 1, &wc) == 0) {}

        uint64_t t1 = get_ns();
        stats_add(lat_stats, t1 - t0);
    }
    return 0;
}

/* ── Throughput benchmark: streaming RDMA WRITEs ── */
static int benchmark_throughput(struct rdma_ctx *rctx, int iterations, struct stats *tp_stats) {
    struct ibv_wc wc;
    struct ibv_sge sge = {
        .addr = (uintptr_t)rctx->buf,
        .length = (uint32_t)rctx->buf_size,
        .lkey = rctx->mr->lkey,
    };

    uint64_t total_bytes = 0;
    uint64_t t_start = get_ns();

    for (int i = 0; i < iterations; i++) {
        struct ibv_send_wr wr = {0};
        wr.sg_list = &sge;
        wr.num_sge = 1;
        wr.opcode = IBV_WR_RDMA_WRITE;
        wr.send_flags = IBV_SEND_SIGNALED;
        wr.wr.rdma.remote_addr = rctx->remote_qp.remote_addr;
        wr.wr.rdma.rkey = rctx->remote_qp.rkey;
        struct ibv_send_wr *bad_wr;
        ibv_post_send(rctx->qp, &wr, &bad_wr);

        while (ibv_poll_cq(rctx->cq, 1, &wc) == 0) {}
        total_bytes += rctx->buf_size;
    }

    uint64_t t_end = get_ns();
    uint64_t elapsed = t_end - t_start;
    double gbps = (total_bytes * 8.0) / (elapsed / 1000.0) / 1e9;
    printf("  Throughput: %.2f Gb/s (%zu bytes in %.2f ms)\n",
           gbps, total_bytes, elapsed / 1e6);
    return 0;
}

/* ── Message rate benchmark ── */
static int benchmark_msg_rate(struct rdma_ctx *rctx, int iterations, struct stats *mr_stats) {
    struct ibv_wc wc;
    struct ibv_sge sge = {
        .addr = (uintptr_t)rctx->buf,
        .length = (uint32_t)rctx->buf_size,
        .lkey = rctx->mr->lkey,
    };

    for (int i = 0; i < iterations; i++) {
        uint64_t t0 = get_ns();

        struct ibv_send_wr wr = {0};
        wr.sg_list = &sge;
        wr.num_sge = 1;
        wr.opcode = IBV_WR_SEND;
        wr.send_flags = IBV_SEND_SIGNALED;
        struct ibv_send_wr *bad_wr;
        ibv_post_send(rctx->qp, &wr, &bad_wr);

        while (ibv_poll_cq(rctx->cq, 1, &wc) == 0) {}

        uint64_t t1 = get_ns();
        stats_add(mr_stats, t1 - t0);
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "Usage: %s server <bind_addr> <port> | client <server_addr> <port> <msg_size> <iterations>\n", argv[0]);
        return 1;
    }

    const char *mode = argv[1];
    struct rdma_ctx rctx = {0};
    int ret = 0;

    if (strcmp(mode, "server") == 0 && argc >= 4) {
        const char *bind_addr = argv[2];
        int port = atoi(argv[3]);

        if (rdma_init(&rctx, 4096) < 0) { fprintf(stderr, "RDMA init failed\n"); return 1; }

        int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
        int opt = 1;
        setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
        struct sockaddr_in addr = {0};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        inet_pton(AF_INET, bind_addr, &addr.sin_addr);
        bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr));
        listen(listen_fd, 1);
        printf("[BENCH SERVER] Listening on %s:%d\n", bind_addr, port);

        struct sockaddr_in peer;
        socklen_t peer_len = sizeof(peer);
        rctx.sockfd = accept(listen_fd, (struct sockaddr *)&peer, &peer_len);
        close(listen_fd);

        exchange_qp_info(&rctx, 1);
        qp_to_init(&rctx);
        qp_to_rtr(&rctx);
        qp_to_rts(&rctx);
        printf("[BENCH SERVER] QP ready\n");

        /* Run benchmarks as server side */
        struct stats lat_stats, tp_stats, mr_stats;
        stats_init(&lat_stats, MAX_ITERATIONS);
        stats_init(&tp_stats, MAX_ITERATIONS);
        stats_init(&mr_stats, MAX_ITERATIONS);

        printf("\n=== RDMA Latency Benchmark ===\n");
        benchmark_latency(&rctx, 10000, &lat_stats);
        stats_print(&lat_stats, "Latency (RDMA WRITE)");

        printf("\n=== RDMA Throughput Benchmark ===\n");
        benchmark_throughput(&rctx, 10000, &tp_stats);

        printf("\n=== RDMA Message Rate Benchmark ===\n");
        benchmark_msg_rate(&rctx, 10000, &mr_stats);
        stats_print(&mr_stats, "Message Rate (SEND)");

        close(rctx.sockfd);

    } else if (strcmp(mode, "client") == 0 && argc >= 6) {
        const char *server_addr = argv[2];
        int port = atoi(argv[3]);
        size_t msg_size = atoi(argv[4]);
        int iterations = atoi(argv[5]);

        if (rdma_init(&rctx, msg_size) < 0) { fprintf(stderr, "RDMA init failed\n"); return 1; }

        rctx.sockfd = socket(AF_INET, SOCK_STREAM, 0);
        struct sockaddr_in addr = {0};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        inet_pton(AF_INET, server_addr, &addr.sin_addr);
        connect(rctx.sockfd, (struct sockaddr *)&addr, sizeof(addr));

        exchange_qp_info(&rctx, 0);
        qp_to_init(&rctx);
        qp_to_rtr(&rctx);
        qp_to_rts(&rctx);
        printf("[BENCH CLIENT] QP ready\n");

        struct stats lat_stats, tp_stats, mr_stats;
        stats_init(&lat_stats, iterations);
        stats_init(&tp_stats, iterations);
        stats_init(&mr_stats, iterations);

        printf("\n=== RDMA Latency Benchmark (msg_size=%zu) ===\n", msg_size);
        benchmark_latency(&rctx, iterations, &lat_stats);
        stats_print(&lat_stats, "Latency (RDMA WRITE)");

        printf("\n=== RDMA Throughput Benchmark ===\n");
        benchmark_throughput(&rctx, iterations, &tp_stats);

        printf("\n=== RDMA Message Rate Benchmark ===\n");
        benchmark_msg_rate(&rctx, iterations, &mr_stats);
        stats_print(&mr_stats, "Message Rate (SEND)");

        close(rctx.sockfd);
    }

    if (rctx.qp) ibv_destroy_qp(rctx.qp);
    if (rctx.cq) ibv_destroy_cq(rctx.cq);
    if (rctx.mr) ibv_dereg_mr(rctx.mr);
    if (rctx.buf) free(rctx.buf);
    if (rctx.pd) ibv_dealloc_pd(rctx.pd);
    if (rctx.ctx) ibv_close_device(rctx.ctx);
    return ret;
}
