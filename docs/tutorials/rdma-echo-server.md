# Tutorial: RDMA Echo Server

**Domain:** Network  
**Difficulty:** Advanced  
**Duration:** 3–4 hours

---

## Overview

In this tutorial, you'll build an RDMA-based echo server that demonstrates zero-copy, kernel-bypass data transfer between two hosts. The server receives data via RDMA READ/WRITE operations and echoes it back without CPU involvement on the data path.

## What You'll Build

- **Server:** Listens for RDMA connections, echoes received data
- **Client:** Connects to server, sends data, receives echo
- **Transport:** Reliable Connection (RC) Queue Pairs

## Prerequisites

- Two hosts with RDMA-capable NICs (Mellanox ConnectX-5/6/7)
- `libibverbs-dev` and `librdmacm-dev` installed
- IP connectivity between hosts
- `ibv_devinfo` shows active ports

---

## Step 1: Verify RDMA Hardware

```bash
# On both hosts
ibv_devinfo
# Should show: state: PORT_ACTIVE, link_layer: Ethernet or InfiniBand

# Test connectivity
ib_write_bw -d mlx5_0  # Server
ib_write_bw -d mlx5_0 <server_ip>  # Client
```

## Step 2: Server Implementation

```c
// rdma_echo_server.c
#include <infiniband/verbs.h>
#include <rdma/rdma_cm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MSG_SIZE 4096
#define QUEUE_DEPTH 16

struct rdma_context {
    struct ibv_context *ctx;
    struct ibv_pd *pd;
    struct ibv_cq *cq;
    struct ibv_qp *qp;
    struct ibv_mr *mr;
    char *buf;
    int sockfd;
};

// Create Queue Pair
struct ibv_qp *create_qp(struct rdma_context *rctx) {
    struct ibv_qp_init_attr qp_attr = {
        .send_cq = rctx->cq,
        .recv_cq = rctx->cq,
        .cap = {
            .max_send_wr = QUEUE_DEPTH,
            .max_recv_wr = QUEUE_DEPTH,
            .max_send_sge = 1,
            .max_recv_sge = 1,
        },
        .qp_type = IBV_QPT_RC,
    };
    return ibv_create_qp(rctx->pd, &qp_attr);
}

// Transition QP through states
int modify_qp_to_init(struct ibv_qp *qp) {
    struct ibv_qp_attr attr = {
        .qp_state = IBV_QPS_INIT,
        .pkey_index = 0,
        .port_num = 1,
        .qp_access_flags = IBV_ACCESS_LOCAL_WRITE |
                          IBV_ACCESS_REMOTE_READ |
                          IBV_ACCESS_REMOTE_WRITE,
    };
    return ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_PKEY_INDEX | IBV_QP_PORT | IBV_QP_ACCESS_FLAGS);
}

int modify_qp_to_rtr(struct ibv_qp *qp, uint32_t remote_qpn,
                     uint16_t dlid, uint8_t *gid) {
    struct ibv_qp_attr attr = {
        .qp_state = IBV_QPS_RTR,
        .path_mtu = IBV_MTU_4096,
        .dest_qp_num = remote_qpn,
        .rq_psn = 0,
        .max_dest_rd_atomic = 1,
        .min_rnr_timer = 12,
        .ah_attr = {
            .is_global = 1,
            .grh = { .gid_index = 0, .hop_limit = 1 },
            .dlid = dlid,
            .sl = 0,
            .src_path_bits = 0,
            .port_num = 1,
        },
    };
    memcpy(attr.ah_attr.grh.dgid.raw, gid, 16);
    return ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU |
        IBV_QP_DEST_QPN | IBV_QP_RQ_PSN |
        IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER);
}

int modify_qp_to_rts(struct ibv_qp *qp) {
    struct ibv_qp_attr attr = {
        .qp_state = IBV_QPS_RTS,
        .timeout = 14,
        .retry_cnt = 7,
        .rnr_retry = 7,
        .sq_psn = 0,
        .max_rd_atomic = 1,
    };
    return ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_TIMEOUT | IBV_QP_RETRY_CNT |
        IBV_QP_RNR_RETRY | IBV_QP_SQ_PSN | IBV_QP_MAX_QP_RD_ATOMIC);
}

// Post receive buffer
int post_recv(struct rdma_context *rctx) {
    struct ibv_sge sge = {
        .addr = (uintptr_t)rctx->buf,
        .length = MSG_SIZE,
        .lkey = rctx->mr->lkey,
    };
    struct ibv_recv_wr wr = {
        .wr_id = 1,
        .sg_list = &sge,
        .num_sge = 1,
    };
    struct ibv_recv_wr *bad_wr;
    return ibv_post_recv(rctx->qp, &wr, &bad_wr);
}

// Send data via RDMA WRITE
int rdma_write(struct rdma_context *rctx, uint64_t remote_addr,
               uint32_t rkey) {
    struct ibv_sge sge = {
        .addr = (uintptr_t)rctx->buf,
        .length = MSG_SIZE,
        .lkey = rctx->mr->lkey,
    };
    struct ibv_send_wr wr = {
        .wr_id = 2,
        .sg_list = &sge,
        .num_sge = 1,
        .opcode = IBV_WR_RDMA_WRITE,
        .send_flags = IBV_SEND_SIGNALED,
        .wr.rdma = {
            .remote_addr = remote_addr,
            .rkey = rkey,
        },
    };
    struct ibv_send_wr *bad_wr;
    return ibv_post_send(rctx->qp, &wr, &bad_wr);
}

// Main server loop
int main(int argc, char **argv) {
    struct rdma_context rctx = {0};
    
    // 1. Get device list
    struct ibv_device **dev_list = ibv_get_device_list(NULL);
    if (!dev_list) { perror("ibv_get_device_list"); return 1; }
    
    // 2. Open device
    rctx.ctx = ibv_open_device(dev_list[0]);
    if (!rctx.ctx) { perror("ibv_open_device"); return 1; }
    
    // 3. Allocate PD
    rctx.pd = ibv_alloc_pd(rctx.ctx);
    
    // 4. Allocate buffer and register MR
    rctx.buf = malloc(MSG_SIZE);
    rctx.mr = ibv_reg_mr(rctx.pd, rctx.buf, MSG_SIZE,
        IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE |
        IBV_ACCESS_REMOTE_READ);
    
    // 5. Create CQ
    rctx.cq = ibv_create_cq(rctx.ctx, QUEUE_DEPTH * 2, NULL, NULL, 0);
    
    // 6. Create QP and transition states
    rctx.qp = create_qp(&rctx);
    modify_qp_to_init(rctx.qp);
    
    // 7. Exchange QP info with client (via TCP socket)
    // ... (socket exchange code omitted for brevity)
    
    modify_qp_to_rtr(rctx.qp, remote_qpn, remote_lid, remote_gid);
    modify_qp_to_rts(rctx.qp);
    
    // 8. Post receive and wait for data
    post_recv(&rctx);
    
    // 9. Poll CQ for completion
    struct ibv_wc wc;
    while (ibv_poll_cq(rctx.cq, 1, &wc) == 0) { /* spin */ }
    
    if (wc.status == IBV_WC_SUCCESS) {
        printf("Received: %s\n", rctx.buf);
        // Echo back
        rdma_write(&rctx, remote_addr, remote_rkey);
    }
    
    // 10. Cleanup
    ibv_dereg_mr(rctx.mr);
    free(rctx.buf);
    ibv_destroy_qp(rctx.qp);
    ibv_destroy_cq(rctx.cq);
    ibv_dealloc_pd(rctx.pd);
    ibv_close_device(rctx.ctx);
    ibv_free_device_list(dev_list);
    
    return 0;
}
```

## Step 3: Client Implementation

```c
// rdma_echo_client.c
// Similar structure to server, but:
// 1. Connect to server via TCP to exchange QP info
// 2. Send data via RDMA WRITE to server
// 3. Wait for echo response
// 4. Verify data integrity

// Key difference: client initiates the RDMA operation
int main(int argc, char **argv) {
    // ... (same initialization as server)
    
    // Connect to server
    int sockfd = connect_to_server(argv[1], 12345);
    
    // Exchange QP info
    exchange_qp_info(sockfd, &local_qp_info, &remote_qp_info);
    
    // Transition QP to RTR and RTS
    modify_qp_to_rtr(qp, remote_qp_info.qpn, remote_qp_info.lid,
                     remote_qp_info.gid);
    modify_qp_to_rts(qp);
    
    // Send data
    strcpy(buf, "Hello RDMA!");
    rdma_write(&rctx, remote_addr, remote_rkey);
    
    // Wait for echo
    struct ibv_wc wc;
    while (ibv_poll_cq(cq, 1, &wc) == 0) { /* spin */ }
    
    printf("Echo: %s\n", buf);
    
    // Cleanup...
    return 0;
}
```

## Step 4: Build and Run

```bash
# Build
gcc -o rdma_server rdma_echo_server.c -libverbs -lrdmacm
gcc -o rdma_client rdma_echo_client.c -libverbs -lrdmacm

# Run server
./rdma_server

# Run client (on second host)
./rdma_client <server_ip>
```

## Step 5: Verify

```bash
# Check RDMA counters
rdma statistic show

# Monitor RDMA traffic
rdma resource show qp
```

## Expected Results

| Metric | Value |
|--------|-------|
| Latency (64B) | 0.78–2.13 µs |
| Throughput (2048B) | 33–37 Gb/s |
| CPU overhead | Near-zero (hardware offload) |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Port not active" | Check `ibv_devinfo`, verify cable |
| "QP transition failed" | Verify GID exchange, check subnet |
| "CQ overflow" | Increase queue depth |
| High latency | Check PFC/ECN configuration for RoCE |

## Next Steps

- Implement RDMA READ for pull-based communication
- Add multiple QPs for parallelism
- Explore InfiniBand for even lower latency
- Move to [P4 Switch Pipeline](p4-switch-pipeline.md) for programmable data plane
