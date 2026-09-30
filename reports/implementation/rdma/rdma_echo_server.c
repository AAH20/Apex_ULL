/**
 * rdma_echo_server.c — Full RDMA Echo Server Implementation
 *
 * Complete RDMA server with:
 * - Queue Pair state machine (RESET → INIT → RTR → RTS)
 * - RDMA WRITE with immediate data
 * - Completion queue polling
 * - TCP control channel for QP info exchange
 * - Multi-message echo with completion verification
 *
 * Build: gcc -O2 -Wall -o rdma_server rdma_echo_server.c -libverbs -lrdmacm
 * Run:   ./rdma_server [bind_addr] [port]
 */

#include <infiniband/verbs.h>
#include <rdma/rdma_cm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>

#define MSG_SIZE        4096
#define QUEUE_DEPTH     32
#define MAX_SGE         4
#define WR_ID_SEND      1
#define WR_ID_RECV      2
#define WR_ID_WRITE     3

/* QP info exchanged over TCP control channel */
struct qp_info {
    uint32_t qp_num;
    uint16_t lid;
    uint8_t  gid[16];
    uint64_t remote_addr;
    uint32_t rkey;
    uint32_t padding;
} __attribute__((packed));

struct rdma_ctx {
    struct ibv_context     *ctx;
    struct ibv_pd          *pd;
    struct ibv_cq          *cq;
    struct ibv_qp          *qp;
    struct ibv_mr          *mr;
    struct ibv_comp_channel *channel;
    char                    buf[MSG_SIZE];
    struct qp_info          local_qp;
    struct qp_info          remote_qp;
    int                     sockfd;
};

/* ── Utility: get time in nanoseconds ── */
static uint64_t get_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

/* ── Utility: print QP state transition error ── */
static void print_qp_error(const char *step, int ret) {
    fprintf(stderr, "[ERROR] %s failed: %s (errno=%d)\n", step, strerror(ret), ret);
}

/* ── Create Queue Pair ── */
static struct ibv_qp *create_qp(struct rdma_ctx *rctx) {
    struct ibv_qp_init_attr qp_attr = {0};
    qp_attr.send_cq = rctx->cq;
    qp_attr.recv_cq = rctx->cq;
    qp_attr.cap.max_send_wr = QUEUE_DEPTH;
    qp_attr.cap.max_recv_wr = QUEUE_DEPTH;
    qp_attr.cap.max_send_sge = MAX_SGE;
    qp_attr.cap.max_recv_sge = MAX_SGE;
    qp_attr.qp_type = IBV_QPT_RC;
    qp_attr.sq_sig_all = 0;  /* Only signal on WRs with IBV_SEND_SIGNALED */

    struct ibv_qp *qp = ibv_create_qp(rctx->pd, &qp_attr);
    if (!qp) {
        print_qp_error("ibv_create_qp", errno);
        return NULL;
    }
    return qp;
}

/* ── Transition QP to INIT ── */
static int qp_to_init(struct rdma_ctx *rctx) {
    struct ibv_qp_attr attr = {0};
    attr.qp_state = IBV_QPS_INIT;
    attr.pkey_index = 0;
    attr.port_num = 1;
    attr.qp_access_flags = IBV_ACCESS_LOCAL_WRITE |
                           IBV_ACCESS_REMOTE_READ |
                           IBV_ACCESS_REMOTE_WRITE;
    int ret = ibv_modify_qp(rctx->qp, &attr,
        IBV_QP_STATE | IBV_QP_PKEY_INDEX | IBV_QP_PORT | IBV_QP_ACCESS_FLAGS);
    if (ret) print_qp_error("INIT", ret);
    return ret;
}

/* ── Transition QP to RTR (Ready To Receive) ── */
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
    attr.ah_attr.grh.sgid_index = 0;
    attr.ah_attr.dlid = rctx->remote_qp.lid;
    attr.ah_attr.sl = 0;
    attr.ah_attr.src_path_bits = 0;
    attr.ah_attr.port_num = 1;

    int ret = ibv_modify_qp(rctx->qp, &attr,
        IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU |
        IBV_QP_DEST_QPN | IBV_QP_RQ_PSN |
        IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER);
    if (ret) print_qp_error("RTR", ret);
    return ret;
}

/* ── Transition QP to RTS (Ready To Send) ── */
static int qp_to_rts(struct rdma_ctx *rctx) {
    struct ibv_qp_attr attr = {0};
    attr.qp_state = IBV_QPS_RTS;
    attr.timeout = 14;
    attr.retry_cnt = 7;
    attr.rnr_retry = 7;
    attr.sq_psn = 0;
    attr.max_rd_atomic = 1;

    int ret = ibv_modify_qp(rctx->qp, &attr,
        IBV_QP_STATE | IBV_QP_TIMEOUT | IBV_QP_RETRY_CNT |
        IBV_QP_RNR_RETRY | IBV_QP_SQ_PSN | IBV_QP_MAX_QP_RD_ATOMIC);
    if (ret) print_qp_error("RTS", ret);
    return ret;
}

/* ── Post receive work request ── */
static int post_recv(struct rdma_ctx *rctx) {
    struct ibv_sge sge = {
        .addr = (uintptr_t)rctx->buf,
        .length = MSG_SIZE,
        .lkey = rctx->mr->lkey,
    };
    struct ibv_recv_wr wr = {0};
    wr.wr_id = WR_ID_RECV;
    wr.sg_list = &sge;
    wr.num_sge = 1;
    struct ibv_recv_wr *bad_wr;
    int ret = ibv_post_recv(rctx->qp, &wr, &bad_wr);
    if (ret) print_qp_error("post_recv", ret);
    return ret;
}

/* ── Post RDMA WRITE with immediate ── */
static int post_rdma_write(struct rdma_ctx *rctx) {
    struct ibv_sge sge = {
        .addr = (uintptr_t)rctx->buf,
        .length = MSG_SIZE,
        .lkey = rctx->mr->lkey,
    };
    struct ibv_send_wr wr = {0};
    wr.wr_id = WR_ID_WRITE;
    wr.sg_list = &sge;
    wr.num_sge = 1;
    wr.opcode = IBV_WR_RDMA_WRITE_WITH_IMM;
    wr.send_flags = IBV_SEND_SIGNALED;
    wr.imm_data = htonl(0xDEADBEEF);
    wr.wr.rdma.remote_addr = rctx->remote_qp.remote_addr;
    wr.wr.rdma.rkey = rctx->remote_qp.rkey;

    struct ibv_send_wr *bad_wr;
    int ret = ibv_post_send(rctx->qp, &wr, &bad_wr);
    if (ret) print_qp_error("post_rdma_write", ret);
    return ret;
}

/* ── Poll CQ for completion ── */
static int poll_cq(struct rdma_ctx *rctx, struct ibv_wc *wc) {
    int ne;
    do {
        ne = ibv_poll_cq(rctx->cq, 1, wc);
    } while (ne == 0);
    if (ne < 0) {
        print_qp_error("ibv_poll_cq", errno);
        return -1;
    }
    if (wc->status != IBV_WC_SUCCESS) {
        fprintf(stderr, "[ERROR] WC failed: %s\n", ibv_wc_status_str(wc->status));
        return -1;
    }
    return 0;
}

/* ── TCP control channel: exchange QP info ── */
static int exchange_qp_info(struct rdma_ctx *rctx, int is_server) {
    if (is_server) {
        /* Server: send local QP info, receive remote QP info */
        if (send(rctx->sockfd, &rctx->local_qp, sizeof(struct qp_info), 0) < 0) {
            perror("send qp_info");
            return -1;
        }
        if (recv(rctx->sockfd, &rctx->remote_qp, sizeof(struct qp_info), 0) < 0) {
            perror("recv qp_info");
            return -1;
        }
    } else {
        /* Client: receive remote QP info, send local QP info */
        if (recv(rctx->sockfd, &rctx->remote_qp, sizeof(struct qp_info), 0) < 0) {
            perror("recv qp_info");
            return -1;
        }
        if (send(rctx->sockfd, &rctx->local_qp, sizeof(struct qp_info), 0) < 0) {
            perror("send qp_info");
            return -1;
        }
    }
    return 0;
}

/* ── Initialize RDMA context ── */
static int rdma_init(struct rdma_ctx *rctx, const char *dev_name) {
    struct ibv_device **dev_list;
    struct ibv_device *ib_dev = NULL;

    dev_list = ibv_get_device_list(NULL);
    if (!dev_list) {
        perror("ibv_get_device_list");
        return -1;
    }
    if (dev_name) {
        for (int i = 0; dev_list[i]; i++) {
            if (strcmp(ibv_get_device_name(dev_list[i]), dev_name) == 0) {
                ib_dev = dev_list[i];
                break;
            }
        }
    } else {
        ib_dev = dev_list[0];
    }
    if (!ib_dev) {
        fprintf(stderr, "No RDMA device found\n");
        ibv_free_device_list(dev_list);
        return -1;
    }

    rctx->ctx = ibv_open_device(ib_dev);
    ibv_free_device_list(dev_list);
    if (!rctx->ctx) {
        perror("ibv_open_device");
        return -1;
    }

    rctx->pd = ibv_alloc_pd(rctx->ctx);
    if (!rctx->pd) { perror("ibv_alloc_pd"); return -1; }

    rctx->mr = ibv_reg_mr(rctx->pd, rctx->buf, MSG_SIZE,
        IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE | IBV_ACCESS_REMOTE_READ);
    if (!rctx->mr) { perror("ibv_reg_mr"); return -1; }

    rctx->cq = ibv_create_cq(rctx->ctx, QUEUE_DEPTH * 2, NULL, NULL, 0);
    if (!rctx->cq) { perror("ibv_create_cq"); return -1; }

    rctx->qp = create_qp(rctx);
    if (!rctx->qp) return -1;

    /* Populate local QP info */
    struct ibv_port_attr port_attr;
    ibv_query_port(rctx->ctx, 1, &port_attr);
    rctx->local_qp.qp_num = rctx->qp->qp_num;
    rctx->local_qp.lid = port_attr.lid;
    rctx->local_qp.remote_addr = (uint64_t)(uintptr_t)rctx->buf;
    rctx->local_qp.rkey = rctx->mr->rkey;
    memset(rctx->local_qp.gid, 0, 16);

    return 0;
}

/* ── Cleanup RDMA context ── */
static void rdma_cleanup(struct rdma_ctx *rctx) {
    if (rctx->qp) ibv_destroy_qp(rctx->qp);
    if (rctx->cq) ibv_destroy_cq(rctx->cq);
    if (rctx->mr) ibv_dereg_mr(rctx->mr);
    if (rctx->pd) ibv_dealloc_pd(rctx->pd);
    if (rctx->ctx) ibv_close_device(rctx->ctx);
}

/* ── Server main loop ── */
static int run_server(struct rdma_ctx *rctx, const char *bind_addr, int port) {
    int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd < 0) { perror("socket"); return -1; }

    int opt = 1;
    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, bind_addr, &addr.sin_addr);

    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind"); close(listen_fd); return -1;
    }
    listen(listen_fd, 1);
    printf("[SERVER] Listening on %s:%d\n", bind_addr, port);

    struct sockaddr_in peer;
    socklen_t peer_len = sizeof(peer);
    rctx->sockfd = accept(listen_fd, (struct sockaddr *)&peer, &peer_len);
    if (rctx->sockfd < 0) { perror("accept"); close(listen_fd); return -1; }
    close(listen_fd);
    printf("[SERVER] Client connected from %s:%d\n",
           inet_ntoa(peer.sin_addr), ntohs(peer.sin_port));

    /* Exchange QP info */
    if (exchange_qp_info(rctx, 1) < 0) return -1;

    /* Transition QP states */
    if (qp_to_init(rctx) < 0) return -1;
    if (qp_to_rtr(rctx) < 0) return -1;
    if (qp_to_rts(rctx) < 0) return -1;
    printf("[SERVER] QP ready (state=RTS)\n");

    /* Post receive */
    if (post_recv(rctx) < 0) return -1;

    /* Echo loop */
    for (int i = 0; i < 10; i++) {
        struct ibv_wc wc;
        if (poll_cq(rctx, &wc) < 0) return -1;
        if (wc.wr_id == WR_ID_RECV) {
            printf("[SERVER] Received message %d: %.64s\n", i, rctx->buf);
            /* Echo back via RDMA WRITE */
            if (post_rdma_write(rctx) < 0) return -1;
            if (poll_cq(rctx, &wc) < 0) return -1;
            if (wc.wr_id == WR_ID_WRITE) {
                printf("[SERVER] Echo sent (RDMA WRITE complete)\n");
            }
            /* Re-post receive */
            if (post_recv(rctx) < 0) return -1;
        }
    }

    close(rctx->sockfd);
    return 0;
}

/* ── Client main loop ── */
static int run_client(struct rdma_ctx *rctx, const char *server_addr, int port) {
    rctx->sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (rctx->sockfd < 0) { perror("socket"); return -1; }

    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, server_addr, &addr.sin_addr);

    if (connect(rctx->sockfd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("connect"); return -1;
    }
    printf("[CLIENT] Connected to %s:%d\n", server_addr, port);

    /* Exchange QP info */
    if (exchange_qp_info(rctx, 0) < 0) return -1;

    /* Transition QP states */
    if (qp_to_init(rctx) < 0) return -1;
    if (qp_to_rtr(rctx) < 0) return -1;
    if (qp_to_rts(rctx) < 0) return -1;
    printf("[CLIENT] QP ready (state=RTS)\n");

    /* Send messages */
    for (int i = 0; i < 10; i++) {
        snprintf(rctx->buf, MSG_SIZE, "Hello RDMA! Message #%d from client", i);

        struct ibv_sge sge = {
            .addr = (uintptr_t)rctx->buf,
            .length = MSG_SIZE,
            .lkey = rctx->mr->lkey,
        };
        struct ibv_send_wr wr = {0};
        wr.wr_id = WR_ID_SEND;
        wr.sg_list = &sge;
        wr.num_sge = 1;
        wr.opcode = IBV_WR_SEND;
        wr.send_flags = IBV_SEND_SIGNALED;

        struct ibv_send_wr *bad_wr;
        if (ibv_post_send(rctx->qp, &wr, &bad_wr) < 0) {
            print_qp_error("post_send", errno);
            return -1;
        }

        struct ibv_wc wc;
        if (poll_cq(rctx, &wc) < 0) return -1;
        if (wc.wr_id == WR_ID_SEND) {
            printf("[CLIENT] Message %d sent\n", i);
        }
    }

    close(rctx->sockfd);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s server <bind_addr> <port> | client <server_addr> <port> [dev_name]\n", argv[0]);
        return 1;
    }

    struct rdma_ctx rctx = {0};
    const char *mode = argv[1];
    int ret;

    if (strcmp(mode, "server") == 0 && argc >= 4) {
        const char *bind_addr = argv[2];
        int port = atoi(argv[3]);
        const char *dev = (argc >= 5) ? argv[4] : NULL;
        if (rdma_init(&rctx, dev) < 0) return 1;
        ret = run_server(&rctx, bind_addr, port);
    } else if (strcmp(mode, "client") == 0 && argc >= 4) {
        const char *server_addr = argv[2];
        int port = atoi(argv[3]);
        const char *dev = (argc >= 5) ? argv[4] : NULL;
        if (rdma_init(&rctx, dev) < 0) return 1;
        ret = run_client(&rctx, server_addr, port);
    } else {
        fprintf(stderr, "Usage: %s server <bind_addr> <port> | client <server_addr> <port> [dev_name]\n", argv[0]);
        return 1;
    }

    rdma_cleanup(&rctx);
    return ret;
}
