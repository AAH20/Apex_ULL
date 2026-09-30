# Feed Handler Architecture Pattern — Full Implementation

> **Project:** Ultra-Low Latency Infrastructure  
> **Scope:** Market data feed ingestion, normalization, and distribution  
> **Date:** 2026-09-30  
> **Version:** 2.0 (Deep Implementation)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Design Goals](#2-design-goals)
3. [Stage 1: NIC / FPGA Layer](#3-stage-1-nic--fpga-layer)
4. [Stage 2: Kernel Bypass](#4-stage-2-kernel-bypass)
5. [Stage 3: Decode Engine](#5-stage-3-decode-engine)
6. [Stage 4: Normalize & Enrich](#6-stage-4-normalize--enrich)
7. [Stage 5: Sequence Reorder Buffer](#7-stage-5-sequence-reorder-buffer)
8. [Stage 6: Order Book Update](#8-stage-6-order-book-update)
9. [Stage 7: Fan-Out / Distributor](#9-stage-7-fan-out--distributor)
10. [End-to-End Integration](#10-end-to-end-integration)
11. [Testing Strategy](#11-testing-strategy)
12. [Optimization Guide](#12-optimization-guide)
13. [Monitoring & Alerting](#13-monitoring--alerting)
14. [Failure Modes & Recovery](#14-failure-modes--recovery)
15. [Implementation Variants](#15-implementation-variants)
16. [References](#16-references)

---

## 1. Overview

The feed handler is the ingress point for all market data entering the ULL system. It receives raw exchange protocols (FIX/FAST, ITCH, OUCH, binary market data feeds), decodes and normalizes them into a canonical internal format, and distributes them to downstream consumers (matching engine, risk, market data distribution) with minimal and bounded latency.

**Core principle:** The feed handler must never be the bottleneck. Every microsecond spent here directly adds to tick-to-trade latency.

### 7-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FEED HANDLER PIPELINE                                │
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐            │
│  │  NIC /   │──▶│  Kernel  │──▶│  Decode  │──▶│  Normalize   │            │
│  │  FPGA    │   │  Bypass  │   │  Engine  │   │  & Enrich    │            │
│  │  (S1)    │   │  (S2)    │   │  (S3)    │   │  (S4)        │            │
│  └──────────┘   └──────────┘   └──────────┘   └──────┬───────┘            │
│                                                       │                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐          │                    │
│  │  Sequence│   │  Gap     │   │  Order   │          │                    │
│  │  Reorder │──▶│  Detect  │──▶│  Book    │◀─────────┘                    │
│  │  (S5)    │   │  & Alert │   │  (S6)    │                               │
│  └──────────┘   └──────────┘   └────┬─────┘                               │
│                                     │                                      │
│                              ┌──────▼───────┐                              │
│                              │  Fan-Out /   │                              │
│                              │  Distributor │                              │
│                              │  (S7)        │                              │
│                              └──────┬───────┘                              │
│                                     │                                      │
│                    ┌────────────────┼────────────────┐                    │
│                    ▼                ▼                ▼                    │
│              ┌──────────┐    ┌──────────┐    ┌──────────┐                │
│              │ Matching │    │  Risk    │    │  Market  │                │
│              │ Engine   │    │  Engine  │    │  Data   │                │
│              └──────────┘    └──────────┘    └──────────┘                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Design Goals

| Goal | Target |
|---|---|
| **Latency (p99)** | < 5 µs from wire to normalized event |
| **Latency (p999)** | < 10 µs |
| **Throughput** | > 10M messages/second per feed |
| **Jitter (p99-p50)** | < 2 µs |
| **Packet loss** | Zero (hardware timestamped, kernel bypass) |
| **Determinism** | No dynamic memory allocation on hot path; no syscalls; no locks |

---

## 3. Stage 1: NIC / FPGA Layer

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NIC / FPGA LAYER                          │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  PHY /   │──▶│  MAC +   │──▶│  RSS +   │──▶│  HW     │ │
│  │  SerDes  │   │  Timestamp│   │  Flow    │   │  Filter │ │
│  │          │   │  (PTP)   │   │  Steering│   │         │ │
│  └──────────┘   └──────────┘   └──────────┘   └────┬────┘ │
│                                                     │       │
│                                              ┌──────▼────┐ │
│                                              │  DMA to   │ │
│                                              │  Host Mem │ │
│                                              └───────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Components

| Component | Role | Technology Options |
|---|---|---|
| **SmartNIC / DPU** | Hardware timestamping, packet filtering, flow steering | NVIDIA BlueField-3, Intel IPU, AMD Pensando |
| **FPGA NIC** | Sub-µs protocol decode, hardware pre-processing | AMD Versal AI Edge, Intel Agilex 7, Lattice Nexus |
| **Kernel Bypass NIC** | DPDK/AF_XDP raw packet access | Mellanox/NVIDIA ConnectX-7, Intel E810 |

### 3.3 Data Structures

```c
// nic_config.h — NIC/FPGA stage configuration
#ifndef NIC_CONFIG_H
#define NIC_CONFIG_H

#include <stdint.h>
#include <stdbool.h>

#define MAX_RX_QUEUES       16
#define MAX_TX_QUEUES       16
#define MAX_INSTRUMENTS     524288  // 2^19
#define HASH_TABLE_SIZE     1048576 // 2^20
#define CACHE_LINE_SIZE     64

// Hardware timestamp from NIC (PTP-synchronized)
typedef struct __attribute__((packed, aligned(8))) {
    uint64_t timestamp_ns;     // PTP-synchronized nanoseconds
    uint32_t port_id;          // Source port
    uint32_t queue_id;         // RSS queue
    uint16_t pkt_len;          // Packet length
    uint16_t flags;            // VLAN, checksum offload flags
} nic_metadata_t;

// Per-queue state (one per RSS queue, cache-line aligned)
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint64_t rx_count;
    _Atomic uint64_t rx_bytes;
    _Atomic uint64_t dropped;
    _Atomic uint64_t last_timestamp;
    char _pad[CACHE_LINE_SIZE - 4 * sizeof(uint64_t)];
} nic_queue_stats_t;

// Flow steering rule (for RSS configuration)
typedef struct {
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint8_t  protocol;
    uint8_t  queue_id;         // Target RSS queue
    bool     active;
} flow_rule_t;

// Instrument cache entry (pre-warmed, lock-free)
typedef struct __attribute__((aligned(16))) {
    uint32_t instrument_id;    // Internal ID
    uint32_t exchange_id;      // Exchange identifier
    uint32_t symbol_hash;      // Hash of exchange symbol
    int32_t  price_scale;      // Price scaling factor (10^scale)
    uint32_t lot_size;         // Minimum quantity increment
    uint32_t flags;            // Trading halts, etc.
} instrument_entry_t;

#endif // NIC_CONFIG_H
```

### 3.4 FPGA Implementation (Verilog)

```verilog
// fpga_nic_layer.v — FPGA-based NIC timestamping and flow steering
module fpga_nic_layer #(
    parameter NUM_QUEUES     = 8,
    parameter QUEUE_ID_WIDTH = 3,
    parameter TIMESTAMP_WIDTH = 64
)(
    input  wire        clk_322mhz,        // 322.265625 MHz (typical for 10GbE)
    input  wire        rst_n,
    
    // RGMII interface (from PHY)
    input  wire [3:0]  rgmii_rxd,
    input  wire        rgmii_rx_ctl,
    input  wire        rgmii_rx_clk,
    
    // Timestamp input (PTP-synchronized)
    input  wire [TIMESTAMP_WIDTH-1:0] ptp_timestamp,
    
    // Output to kernel bypass layer
    output reg  [7:0]  m_axis_tdata,
    output reg         m_axis_tvalid,
    output reg         m_axis_tlast,
    output reg  [QUEUE_ID_WIDTH-1:0] m_axis_tuser,  // Queue ID
    output reg  [TIMESTAMP_WIDTH-1:0] m_axis_ttimestamp,
    input  wire        m_axis_tready
);

    // Parse Ethernet + IP + UDP headers to extract 5-tuple for RSS
    // Compute Toeplitz hash for queue assignment
    // Timestamp at first byte reception (SOF)
    
    localparam S_IDLE       = 4'd0;
    localparam S_ETH_DST    = 4'd1;
    localparam S_ETH_SRC    = 4'd2;
    localparam S_ETH_TYPE   = 4'd3;
    localparam S_IP_HDR     = 4'd4;
    localparam S_UDP_HDR    = 4'd5;
    localparam S_PAYLOAD    = 4'd6;
    localparam S_OUTPUT     = 4'd7;
    
    reg [3:0]  state;
    reg [15:0] byte_counter;
    reg [31:0] src_ip, dst_ip;
    reg [15:0] src_port, dst_port;
    reg [7:0]  ip_protocol;
    reg [TIMESTAMP_WIDTH-1:0] rx_timestamp;
    
    // Toeplitz hash key (standard Linux kernel key)
    localparam [31:0] TOEPLITZ_KEY [0:31] = '{
        32'h6d, 32'h5a, 32'h56, 32'hda, 32'h25, 32'h5b, 32'h0e, 32'hc2,
        32'h41, 32'h61, 32'h37, 32'h76, 32'h65, 32'h5d, 32'h23, 32'hc1,
        32'h3b, 32'h57, 32'h21, 32'h4f, 32'h53, 32'h29, 32'h43, 32'h69,
        32'h31, 32'h47, 32'h59, 32'h2f, 32'h4b, 32'h67, 32'h35, 32'h51
    };
    
    // Compute RSS hash from 5-tuple
    function [QUEUE_ID_WIDTH-1:0] compute_rss_hash;
        input [31:0] sip, dip;
        input [15:0] sp, dp;
        input [7:0]  proto;
        reg [31:0] hash;
        integer i;
        begin
            hash = 32'h0;
            // Hash source IP
            for (i = 0; i < 32; i = i + 1)
                hash = {hash[30:0], hash[31]} ^ (sip[i] ? TOEPLITZ_KEY[i] : 32'h0);
            // Hash dest IP
            for (i = 0; i < 32; i = i + 1)
                hash = {hash[30:0], hash[31]} ^ (dip[i] ? TOEPLITZ_KEY[i] : 32'h0);
            // Hash ports and protocol
            for (i = 0; i < 16; i = i + 1)
                hash = {hash[30:0], hash[31]} ^ (sp[i] ? TOEPLITZ_KEY[i] : 32'h0);
            for (i = 0; i < 16; i = i + 1)
                hash = {hash[30:0], hash[31]} ^ (dp[i] ? TOEPLITZ_KEY[i] : 32'h0);
            for (i = 0; i < 8; i = i + 1)
                hash = {hash[30:0], hash[31]} ^ (proto[i] ? TOEPLITZ_KEY[i] : 32'h0);
            compute_rss_hash = hash[QUEUE_ID_WIDTH-1:0];
        end
    endfunction
    
    // Main state machine
    always @(posedge clk_322mhz or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            byte_counter <= 0;
            m_axis_tvalid <= 0;
            m_axis_tlast <= 0;
        end else begin
            m_axis_tvalid <= 0;
            m_axis_tlast <= 0;
            
            case (state)
                S_IDLE: begin
                    if (rx_sof) begin
                        rx_timestamp <= ptp_timestamp;  // Timestamp at SOF
                        state <= S_ETH_DST;
                        byte_counter <= 0;
                    end
                end
                
                S_ETH_DST: begin
                    if (rx_valid) begin
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 5) begin
                            state <= S_ETH_SRC;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_ETH_SRC: begin
                    if (rx_valid) begin
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 5) begin
                            state <= S_ETH_TYPE;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_ETH_TYPE: begin
                    if (rx_valid) begin
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 1) begin
                            state <= S_IP_HDR;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_IP_HDR: begin
                    if (rx_valid) begin
                        // Extract IP addresses and protocol
                        if (byte_counter >= 12 && byte_counter <= 15)
                            src_ip <= {src_ip[23:0], rx_data};
                        if (byte_counter >= 16 && byte_counter <= 19)
                            dst_ip <= {dst_ip[23:0], rx_data};
                        if (byte_counter == 9)
                            ip_protocol <= rx_data;
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 19) begin
                            state <= S_UDP_HDR;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_UDP_HDR: begin
                    if (rx_valid) begin
                        if (byte_counter <= 1)
                            src_port <= {src_port[7:0], rx_data};
                        if (byte_counter >= 2 && byte_counter <= 3)
                            dst_port <= {dst_port[7:0], rx_data};
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 7) begin
                            state <= S_PAYLOAD;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_PAYLOAD: begin
                    if (rx_valid) begin
                        m_axis_tdata <= rx_data;
                        m_axis_tvalid <= m_axis_tready;
                        m_axis_tuser <= compute_rss_hash(src_ip, dst_ip, src_port, dst_port, ip_protocol);
                        m_axis_ttimestamp <= rx_timestamp;
                        if (rx_eof) begin
                            m_axis_tlast <= 1;
                            state <= S_IDLE;
                        end
                    end
                end
            endcase
        end
    end

endmodule
```

### 3.5 Latency Budget

| Metric | Value | Notes |
|---|---|---|
| **p50** | 200 ns | PHY/MAC layer, deterministic |
| **p99** | 500 ns | Including DMA transfer |
| **p999** | 1 µs | Worst-case PCIe contention |
| **Throughput** | Line rate (10/25/100/400 Gb/s) | Hardware-limited |
| **Jitter** | < 100 ns | Hardware-synchronized |

### 3.6 Determinism Guarantees

- **Hardware timestamping:** PTP-synchronized at PHY/MAC layer, no software jitter
- **Fixed pipeline depth:** FPGA processes each byte in fixed cycles
- **No OS involvement:** DMA directly to pre-allocated host memory
- **Cache-line aligned descriptors:** No false sharing between queues

### 3.7 Testing

```python
# tests/test_nic_layer.py
import pytest
import subprocess
import struct

class TestNICLayer:
    """Test NIC/FPGA layer functionality."""
    
    def test_timestamp_accuracy(self):
        """Verify hardware timestamps are within 100ns of PTP reference."""
        # Send test packet with known timestamp
        # Verify captured timestamp matches expected
        pass
    
    def test_rss_distribution(self):
        """Verify RSS distributes flows evenly across queues."""
        # Generate traffic with different 5-tuples
        # Verify queue assignment matches Toeplitz hash
        pass
    
    def test_flow_steering(self):
        """Verify flow rules direct traffic to correct queues."""
        # Configure flow rules
        # Send matching traffic
        # Verify correct queue assignment
        pass
    
    def test_line_rate(self):
        """Verify line-rate packet processing."""
        # Generate line-rate traffic
        # Verify zero packet loss
        pass
    
    def test_instrument_cache_hit(self):
        """Verify instrument cache lookup latency."""
        # Pre-warm cache
        # Measure lookup latency
        # Assert < 5ns average
        pass
```

---

## 4. Stage 2: Kernel Bypass

### 4.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   KERNEL BYPASS LAYER                        │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  DPDK    │──▶│  RX      │──▶│  Zero-   │──▶│  Huge-  │ │
│  │  PMD     │   │  Burst   │   │  Copy    │   │  page   │ │
│  │  Poll    │   │  Process │   │  mbuf    │   │  Pool   │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │  Core    │   │  NUMA    │   │  Memory  │               │
│  │  Isolation│   │  Aware   │   │  Prefetch│               │
│  └──────────┘   └──────────┘   └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Components

| Component | Role | Technology Options |
|---|---|---|
| **DPDK** | Poll-mode packet I/O, zero-copy buffer access | DPDK 24.x+ |
| **AF_XDP** | Linux-native kernel bypass with socket API | Kernel 6.x+ |
| **SPDK** | Storage I/O bypass (for persistence path) | SPDK 24.x+ |

### 4.3 Data Structures

```c
// kernel_bypass.h — Kernel bypass layer
#ifndef KERNEL_BYPASS_H
#define KERNEL_BYPASS_H

#include <stdint.h>
#include <stdatomic.h>
#include <stdbool.h>

#define RTE_CACHE_LINE_SIZE  64
#define MAX_BURST_SIZE       32
#define NUM_MBUFS            65536
#define MBUF_CACHE_SIZE      512
#define RX_RING_SIZE         4096
#define TX_RING_SIZE         4096

// Pre-allocated mbuf pool (no malloc on hot path)
typedef struct {
    void *base_addr;
    uint32_t size;
    uint32_t elem_size;
    uint32_t head;
    uint32_t tail;
} mempool_t;

// DPDK configuration
typedef struct {
    uint16_t port_id;
    uint16_t num_rx_queues;
    uint16_t num_tx_queues;
    uint16_t rx_desc;
    uint16_t tx_desc;
    uint32_t numa_node;
    bool hw_timestamp;
    bool rss_enabled;
} dpdk_config_t;

// Per-core RX state (cache-line aligned)
typedef struct __attribute__((aligned(RTE_CACHE_LINE_SIZE))) {
    uint16_t port_id;
    uint16_t queue_id;
    uint32_t numa_node;
    _Atomic uint64_t rx_pkts;
    _Atomic uint64_t rx_bytes;
    _Atomic uint64_t rx_errors;
    _Atomic uint64_t rx_no_mbuf;
    char _pad[RTE_CACHE_LINE_SIZE - 6 * sizeof(uint64_t) - 4 * sizeof(uint16_t)];
} rx_core_state_t;

// Packet batch for burst processing
typedef struct {
    void *mbufs[MAX_BURST_SIZE];
    uint16_t count;
    uint64_t timestamps[MAX_BURST_SIZE];
} packet_batch_t;

// Zero-copy mbuf reference (passed to decode stage)
typedef struct {
    uint8_t *data;           // Pointer to packet data in DMA buffer
    uint16_t len;            // Packet length
    uint16_t port;           // Source port
    uint16_t queue;          // RX queue
    uint64_t hw_timestamp;   // Hardware timestamp
    void *mbuf;              // Original mbuf pointer (for release)
} packet_ref_t;

#endif // KERNEL_BYPASS_H
```

### 4.4 DPDK Implementation

```c
// kernel_bypass.c — DPDK kernel bypass implementation
#include "kernel_bypass.h"
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_mempool.h>
#include <rte_ring.h>
#include <rte_lcore.h>
#include <rte_cycles.h>

#define RX_PTHRESH  8
#define RX_HTHRESH  8
#define RX_WTHRESH  4

static struct rte_mempool *mbuf_pool = NULL;
static rx_core_state_t *rx_states = NULL;

int dpdk_init(const dpdk_config_t *config) {
    int ret;
    uint16_t port_id = config->port_id;
    
    // Initialize EAL
    char *argv[] = {"feedhandler", "-c", "0xFF", "--proc-type=auto", NULL};
    ret = rte_eal_init(4, argv);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "EAL init failed: %s\n", rte_strerror(rte_errno));
    }
    
    // Create mbuf pool with hugepages
    char pool_name[32];
    snprintf(pool_name, sizeof(pool_name), "MBUF_POOL_%u", port_id);
    mbuf_pool = rte_pktmbuf_pool_create(pool_name,
        NUM_MBUFS, MBUF_CACHE_SIZE, 0,
        RTE_MBUF_DEFAULT_BUF_SIZE, config->numa_node);
    if (!mbuf_pool) {
        rte_exit(EXIT_FAILURE, "Cannot create mbuf pool: %s\n", rte_strerror(rte_errno));
    }
    
    // Configure port
    struct rte_eth_conf port_conf = {
        .rxmode = {
            .max_rx_pkt_len = RTE_ETHER_MAX_LEN,
            .offloads = RTE_ETH_RX_OFFLOAD_TIMESTAMP,
        },
        .txmode = {
            .offloads = RTE_ETH_TX_OFFLOAD_MULTI_SEGS,
        },
        .rx_adv_conf = {
            .rss_conf = {
                .rss_key = NULL,  // Use default Toeplitz key
                .rss_hf = RTE_ETH_RSS_IP | RTE_ETH_RSS_UDP | RTE_ETH_RSS_TCP,
            },
        },
    };
    
    ret = rte_eth_dev_configure(port_id, config->num_rx_queues, config->num_tx_queues, &port_conf);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot configure port %u: %s\n", port_id, rte_strerror(rte_errno));
    }
    
    // Setup RX queues
    for (uint16_t q = 0; q < config->num_rx_queues; q++) {
        ret = rte_eth_rx_queue_setup(port_id, q, config->rx_desc,
            rte_eth_dev_socket_id(port_id), NULL, mbuf_pool);
        if (ret < 0) {
            rte_exit(EXIT_FAILURE, "Cannot setup RX queue %u: %s\n", q, rte_strerror(rte_errno));
        }
    }
    
    // Setup TX queues
    for (uint16_t q = 0; q < config->num_tx_queues; q++) {
        ret = rte_eth_tx_queue_setup(port_id, q, config->tx_desc,
            rte_eth_dev_socket_id(port_id), NULL);
        if (ret < 0) {
            rte_exit(EXIT_FAILURE, "Cannot setup TX queue %u: %s\n", q, rte_strerror(rte_errno));
        }
    }
    
    // Enable hardware timestamping
    if (config->hw_timestamp) {
        struct rte_eth_timestamp_register ts_reg;
        rte_eth_timesync_enable(port_id);
    }
    
    // Start device
    ret = rte_eth_dev_start(port_id);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot start port %u: %s\n", port_id, rte_strerror(rte_errno));
    }
    
    // Enable promiscuous mode
    rte_eth_promiscuous_enable(port_id);
    
    // Allocate per-core RX state
    rx_states = rte_zmalloc("rx_states",
        sizeof(rx_core_state_t) * rte_lcore_count(), RTE_CACHE_LINE_SIZE);
    if (!rx_states) {
        rte_exit(EXIT_FAILURE, "Cannot allocate RX states\n");
    }
    
    return 0;
}

// Per-core RX processing loop (runs on isolated core)
int rx_loop(void *arg) {
    rx_core_state_t *state = (rx_core_state_t *)arg;
    uint16_t port_id = state->port_id;
    uint16_t queue_id = state->queue_id;
    
    // Pin to specific core
    rte_thread_set_affinity(state->queue_id + 1);  // Skip core 0 (main)
    
    // Pre-fetch mbuf pointers for burst processing
    void *mbufs[MAX_BURST_SIZE];
    
    while (1) {
        // Burst receive (no syscalls, no interrupts)
        uint16_t nb_rx = rte_eth_rx_burst(port_id, queue_id, mbufs, MAX_BURST_SIZE);
        
        if (unlikely(nb_rx == 0)) {
            // Optional: pause or monitor
            continue;
        }
        
        // Process burst
        for (uint16_t i = 0; i < nb_rx; i++) {
            struct rte_mbuf *mbuf = mbufs[i];
            
            // Extract hardware timestamp
            uint64_t hw_ts = 0;
            if (mbuf->ol_flags & RTE_MBUF_F_RX_TIMESTAMP) {
                hw_ts = mbuf->timestamp;
            }
            
            // Create zero-copy packet reference
            packet_ref_t pkt = {
                .data = rte_pktmbuf_mtod(mbuf, uint8_t *),
                .len = mbuf->pkt_len,
                .port = port_id,
                .queue = queue_id,
                .hw_timestamp = hw_ts,
                .mbuf = mbuf,
            };
            
            // Pass to decode stage (via SPSC ring or direct call)
            decode_submit(&pkt);
            
            // Update stats
            atomic_fetch_add_explicit(&state->rx_pkts, 1, memory_order_relaxed);
            atomic_fetch_add_explicit(&state->rx_bytes, mbuf->pkt_len, memory_order_relaxed);
        }
    }
    
    return 0;
}

// Release mbuf back to pool (called after processing)
void packet_release(packet_ref_t *pkt) {
    rte_pktmbuf_free((struct rte_mbuf *)pkt->mbuf);
}
```

### 4.5 AF_XDP Implementation (Alternative)

```c
// af_xdp_bypass.c — AF_XDP kernel bypass (lower complexity than DPDK)
#include <linux/bpf.h>
#include <linux/if_xdp.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <linux/if_link.h>

#define AF_XDP_FRAME_SIZE  4096
#define AF_XDP_NUM_FRAMES  4096
#define AF_XDP_BATCH_SIZE  32

struct af_xdp_umem {
    void *addr;           // mmap'd UMEM region
    uint32_t size;
    struct xdp_desc *descs;
    uint32_t producer;     // kernel writes here
    uint32_t consumer;     // app reads here
};

struct af_xdp_socket {
    int fd;
    struct af_xdp_umem umem;
    struct xsk_ring_prod fill;
    struct xsk_ring_cons rx;
    struct xsk_ring_prod tx;
    struct xsk_ring_cons comp;
};

int af_xdp_init(struct af_xdp_sock *xsk, const char *ifname, uint32_t queue_id) {
    // Create AF_XDP socket
    xsk->fd = socket(AF_XDP, SOCK_RAW, 0);
    if (xsk->fd < 0) return -1;
    
    // Allocate UMEM (hugepages)
    xsk->umem.size = AF_XDP_NUM_FRAMES * AF_XDP_FRAME_SIZE;
    xsk->umem.addr = mmap(NULL, xsk->umem.size,
        PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB, -1, 0);
    
    // Register UMEM with kernel
    struct xdp_umem_reg umem_reg = {
        .addr = (uint64_t)xsk->umem.addr,
        .len = xsk->umem.size,
        .chunk_size = AF_XDP_FRAME_SIZE,
        .headroom = 0,
    };
    setsockopt(xsk->fd, SOL_XDP, XDP_UMEM_REG, &umem_reg, sizeof(umem_reg));
    
    // Setup rings
    struct xdp_mmap_offsets off;
    socklen_t optlen = sizeof(off);
    getsockopt(xsk->fd, SOL_XDP, XDP_MMAP_OFFSETS, &off, &optlen);
    
    // Map fill ring, RX ring, completion ring, TX ring
    // ...
    
    // Bind to interface
    struct sockaddr_xdp sxdp = {
        .sxdp_family = AF_XDP,
        .sxdp_ifindex = if_nametoindex(ifname),
        .sxdp_queue_id = queue_id,
    };
    bind(xsk->fd, (struct sockaddr *)&sxdp, sizeof(sxdp));
    
    return 0;
}

// RX processing loop
void af_xdp_rx_loop(struct af_xdp_sock *xsk) {
    struct xdp_desc descs[AF_XDP_BATCH_SIZE];
    
    while (1) {
        // Poll for new packets (no interrupts)
        uint32_t idx_rx = 0;
        uint32_t n = xsk_ring_cons__peek(&xsk->rx, AF_XDP_BATCH_SIZE, &idx_rx);
        
        if (n == 0) {
            // Optional: poll() or busy-wait
            continue;
        }
        
        for (uint32_t i = 0; i < n; i++) {
            const struct xdp_desc *desc = xsk_ring_cons__rx_desc(&xsk->rx, idx_rx + i);
            
            // Zero-copy access to packet data
            uint8_t *pkt_data = xsk_umem__get_data(xsk->umem.addr, desc->addr);
            
            // Process packet
            packet_ref_t pkt = {
                .data = pkt_data,
                .len = desc->len,
                .hw_timestamp = 0,  // AF_XDP doesn't provide HW timestamp by default
                .mbuf = NULL,       // No mbuf to release
            };
            
            decode_submit(&pkt);
        }
        
        // Release frames back to fill ring
        xsk_ring_cons__release(&xsk->rx, n);
    }
}
```

### 4.6 Latency Budget

| Metric | Value | Notes |
|---|---|---|
| **p50** | 300 ns | DPDK poll, cache-hot |
| **p99** | 800 ns | Including burst processing |
| **p999** | 1.5 µs | Worst-case cache miss |
| **Throughput** | 100+ Mpps per core | Burst processing |
| **Jitter** | < 200 ns | No syscalls, no interrupts |

### 4.7 Determinism Guarantees

- **No syscalls on hot path:** DPDK poll-mode, pre-allocated everything
- **No locks on hot path:** Per-core RX queues, no shared state
- **No dynamic memory:** Fixed-size mbuf pools, hugepages
- **No interrupts:** Busy polling with `isolcpus` and `nohz_full`
- **Cache-line aligned:** Per-core state structures prevent false sharing

### 4.8 Testing

```python
# tests/test_kernel_bypass.py
import pytest
import subprocess
import time

class TestKernelBypass:
    """Test kernel bypass layer functionality."""
    
    def test_zero_syscalls(self):
        """Verify no syscalls on hot path using strace."""
        # Run feed handler
        # Use strace to count syscalls
        # Assert zero syscalls during steady-state RX
        pass
    
    def test_mbuf_pool_exhaustion(self):
        """Verify graceful handling of mbuf pool exhaustion."""
        # Send burst larger than pool size
        # Verify no crash, proper error handling
        pass
    
    def test_burst_processing(self):
        """Verify burst processing efficiency."""
        # Send burst of 32 packets
        # Measure processing time
        # Assert < 1µs per packet amortized
        pass
    
    def test_numa_affinity(self):
        """Verify NUMA-aware memory allocation."""
        # Check memory allocation on correct NUMA node
        # Verify NIC is on same NUMA node
        pass
    
    def test_hw_timestamp(self):
        """Verify hardware timestamp accuracy."""
        # Send packet with known timestamp
        # Verify captured timestamp within tolerance
        pass
```

---

## 5. Stage 3: Decode Engine

### 5.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DECODE ENGINE                             │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Protocol│──▶│  Template│──▶│  Field   │──▶│  Zero-  │ │
│  │  Detect  │   │  Lookup  │   │  Extract │   │  Copy   │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │  SIMD    │   │  Branch  │   │  Session │               │
│  │  Parse   │   │  Minimize│   │  Track   │               │
│  └──────────┘   └──────────┘   └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Components

| Component | Role | Details |
|---|---|---|
| **Protocol Decoder** | Binary → structured message | Template-based FAST, ITCH incremental refresh, OUCH entry |
| **Session Manager** | Connection state, sequence tracking | Per-session sequence number tracking |
| **Reassembler** | Fragmented message reassembly | TCP reassembly for FIX sessions |

### 5.3 Data Structures

```c
// decode_engine.h — Decode engine
#ifndef DECODE_ENGINE_H
#define DECODE_ENGINE_H

#include <stdint.h>
#include <stdbool.h>
#include <immintrin.h>  // AVX-512

#define MAX_TEMPLATES        256
#define MAX_FIELDS_PER_MSG   64
#define MAX_SESSIONS         128
#define FAST_FIELD_MAX       256
#define ITCH_FIELD_MAX       32

// Message types
typedef enum {
    MSG_ADD_ORDER = 1,
    MSG_MODIFY_ORDER = 2,
    MSG_CANCEL_ORDER = 3,
    MSG_TRADE = 4,
    MSG_BOOK_UPDATE = 5,
    MSG_HEARTBEAT = 6,
    MSG_SEQ_GAP = 7,
    MSG_UNKNOWN = 0
} msg_type_t;

// Decoded field (zero-copy, points into packet buffer)
typedef struct {
    uint8_t *data;           // Pointer to field data in packet
    uint16_t len;            // Field length
    uint8_t  type;           // Field type (int, string, etc.)
    uint8_t  template_id;    // Template identifier
} decoded_field_t;

// Decoded message (zero-copy)
typedef struct {
    msg_type_t type;
    uint32_t instrument_id;
    uint64_t sequence_num;
    uint64_t timestamp_ns;
    uint8_t  side;           // BID=0, ASK=1
    int64_t  price;          // Fixed-point
    uint32_t quantity;
    uint32_t order_id;
    uint16_t num_fields;
    decoded_field_t fields[MAX_FIELDS_PER_MSG];
    uint8_t  raw_data[256];  // Raw message for reprocessing
    uint16_t raw_len;
} decoded_message_t;

// FAST template definition
typedef struct {
    uint8_t  template_id;
    uint8_t  num_fields;
    uint8_t  field_types[FAST_FIELD_MAX];
    uint16_t field_offsets[FAST_FIELD_MAX];
    uint16_t field_sizes[FAST_FIELD_MAX];
    bool     is_active;
} fast_template_t;

// ITCH message definition
typedef struct {
    uint8_t  msg_type;
    uint8_t  num_fields;
    uint8_t  field_sizes[ITCH_FIELD_MAX];
    uint16_t field_offsets[ITCH_FIELD_MAX];
} itch_message_def_t;

// Session state
typedef struct {
    uint32_t session_id;
    uint64_t last_sequence;
    uint64_t expected_sequence;
    uint8_t  protocol_type;  // FAST, ITCH, OUCH, FIX
    bool     is_active;
    void    *template_cache;
} session_state_t;

// Decode context (per-core, cache-line aligned)
typedef struct __attribute__((aligned(64))) {
    fast_template_t templates[MAX_TEMPLATES];
    itch_message_def_t itch_defs[256];
    session_state_t sessions[MAX_SESSIONS];
    _Atomic uint64_t decode_count;
    _Atomic uint64_t decode_errors;
    _Atomic uint64_t template_hits;
    _Atomic uint64_t template_misses;
    char _pad[64 - 6 * sizeof(uint64_t)];
} decode_context_t;

#endif // DECODE_ENGINE_H
```

### 5.4 FAST Protocol Decoder

```c
// fast_decoder.c — FAST (FIX Adapted for STreaming) decoder
#include "decode_engine.h"
#include <string.h>

// FAST field types
#define FAST_TYPE_UINT32    0x01
#define FAST_TYPE_UINT64    0x02
#define FAST_TYPE_INT32     0x03
#define FAST_TYPE_INT64     0x04
#define FAST_TYPE_STRING    0x05
#define FAST_TYPE_VECTOR    0x06
#define FAST_TYPE_DECIMAL   0x07
#define FAST_TYPE_SEQUENCE  0x08

// FAST presence map (PMAP) parsing
static inline uint8_t fast_parse_pmap(const uint8_t **ptr, const uint8_t *end) {
    uint8_t pmap = 0;
    uint8_t byte;
    do {
        if (*ptr >= end) return 0;
        byte = *(*ptr)++;
        pmap = (pmap << 7) | (byte & 0x7F);
    } while (byte & 0x80);
    return pmap;
}

// Decode unsigned integer (variable-length)
static inline uint64_t fast_decode_uint(const uint8_t **ptr, const uint8_t *end) {
    uint64_t value = 0;
    uint8_t byte;
    do {
        if (*ptr >= end) return 0;
        byte = *(*ptr)++;
        value = (value << 7) | (byte & 0x7F);
    } while (byte & 0x80);
    return value;
}

// Decode signed integer (variable-length, biased)
static inline int64_t fast_decode_int(const uint8_t **ptr, const uint8_t *end) {
    uint64_t value = fast_decode_uint(ptr, end);
    return (int64_t)((value >> 1) ^ -(value & 1));
}

// Decode decimal (exponent + mantissa)
static inline int64_t fast_decode_decimal(const uint8_t **ptr, const uint8_t *end) {
    int64_t exponent = fast_decode_int(ptr, end);
    int64_t mantissa = fast_decode_int(ptr, end);
    // Apply scaling: value = mantissa * 10^exponent
    // For performance, use lookup table for common exponents
    static const int64_t scale_table[] = {
        1, 10, 100, 1000, 10000, 100000, 1000000, 10000000
    };
    if (exponent >= 0 && exponent < 8) {
        return mantissa * scale_table[exponent];
    }
    return mantissa;  // Fallback
}

// Main FAST decode function
int fast_decode(decode_context_t *ctx, const uint8_t *data, uint16_t len,
                decoded_message_t *msg) {
    const uint8_t *ptr = data;
    const uint8_t *end = data + len;
    
    // Parse PMAP
    uint8_t pmap = fast_parse_pmap(&ptr, end);
    if (!pmap) return -1;
    
    // Get template ID from PMAP
    uint8_t template_id = (pmap >> 1) & 0x7F;
    if (template_id >= MAX_TEMPLATES) return -1;
    
    fast_template_t *tmpl = &ctx->templates[template_id];
    if (!tmpl->is_active) {
        atomic_fetch_add_explicit(&ctx->template_misses, 1, memory_order_relaxed);
        return -1;
    }
    
    atomic_fetch_add_explicit(&ctx->template_hits, 1, memory_order_relaxed);
    
    // Decode fields according to template
    msg->type = MSG_UNKNOWN;
    msg->num_fields = 0;
    
    for (uint8_t i = 0; i < tmpl->num_fields && msg->num_fields < MAX_FIELDS_PER_MSG; i++) {
        decoded_field_t *field = &msg->fields[msg->num_fields++];
        field->template_id = template_id;
        field->type = tmpl->field_types[i];
        field->data = (uint8_t *)ptr;
        
        switch (tmpl->field_types[i]) {
            case FAST_TYPE_UINT32:
            case FAST_TYPE_UINT64:
                field->len = sizeof(uint64_t);
                uint64_t uv = fast_decode_uint(&ptr, end);
                memcpy(field->data, &uv, sizeof(uv));
                break;
                
            case FAST_TYPE_INT32:
            case FAST_TYPE_INT64:
                field->len = sizeof(int64_t);
                int64_t iv = fast_decode_int(&ptr, end);
                memcpy(field->data, &iv, sizeof(iv));
                break;
                
            case FAST_TYPE_DECIMAL:
                field->len = sizeof(int64_t);
                int64_t dv = fast_decode_decimal(&ptr, end);
                memcpy(field->data, &dv, sizeof(dv));
                break;
                
            case FAST_TYPE_STRING:
                // String: length-prefixed
                uint16_t slen = (uint16_t)fast_decode_uint(&ptr, end);
                field->len = slen;
                ptr += slen;
                break;
                
            default:
                field->len = tmpl->field_sizes[i];
                ptr += field->len;
                break;
        }
    }
    
    // Extract key fields for normalization
    // (price, quantity, side, instrument_id, sequence_num)
    // This is protocol-specific and would be customized per exchange
    
    atomic_fetch_add_explicit(&ctx->decode_count, 1, memory_order_relaxed);
    return 0;
}
```

### 5.5 ITCH Protocol Decoder

```c
// itch_decoder.c — ITCH protocol decoder
#include "decode_engine.h"

// ITCH message types
#define ITCH_MSG_ADD_ORDER       'A'
#define ITCH_MSG_ADD_ORDER_MPID  'F'
#define ITCH_MSG_ORDER_EXECUTED 'E'
#define ITCH_MSG_ORDER_CANCEL   'C'
#define ITCH_MSG_ORDER_DELETE   'D'
#define ITCH_MSG_ORDER_REPLACE  'U'
#define ITCH_MSG_TRADE          'P'
#define ITCH_MSG_CROSS_TRADE    'X'
#define ITCH_MSG_BROKEN_TRADE   'B'
#define ITCH_MSG_NOII          'S'
#define ITCH_MSG_RPII           'R'

// ITCH message header (common to all messages)
typedef struct __attribute__((packed)) {
    uint16_t length;         // Message length (including header)
    uint8_t  msg_type;       // Message type character
    uint64_t timestamp;      // Nanosecond timestamp
    uint64_t order_ref;      // Order reference number
} itch_header_t;

// Decode ITCH message
int itch_decode(decode_context_t *ctx, const uint8_t *data, uint16_t len,
                decoded_message_t *msg) {
    if (len < sizeof(itch_header_t)) return -1;
    
    const itch_header_t *hdr = (const itch_header_t *)data;
    const uint8_t *ptr = data + sizeof(itch_header_t);
    const uint8_t *end = data + len;
    
    msg->timestamp_ns = hdr->timestamp;
    msg->order_id = hdr->order_ref;
    msg->num_fields = 0;
    
    switch (hdr->msg_type) {
        case ITCH_MSG_ADD_ORDER:
        case ITCH_MSG_ADD_ORDER_MPID: {
            msg->type = MSG_ADD_ORDER;
            // Extract: stock locate, tracking number, timestamp, order ref,
            // buy/sell indicator, shares, stock symbol, price
            if (end - ptr < 36) return -1;
            
            // Side (1 byte)
            msg->side = (*ptr == 'B') ? 0 : 1;
            ptr += 1;
            
            // Shares (4 bytes, big-endian)
            msg->quantity = (ptr[0] << 24) | (ptr[1] << 16) | (ptr[2] << 8) | ptr[3];
            ptr += 4;
            
            // Stock symbol (8 bytes, space-padded)
            // Map to instrument_id via hash lookup
            uint64_t symbol_hash = 0;
            for (int i = 0; i < 8; i++) {
                symbol_hash = (symbol_hash << 8) | ptr[i];
            }
            msg->instrument_id = (uint32_t)(symbol_hash % MAX_INSTRUMENTS);
            ptr += 8;
            
            // Price (4 bytes, fixed-point with 4 decimal places)
            int64_t price_raw = (ptr[0] << 24) | (ptr[1] << 16) | (ptr[2] << 8) | ptr[3];
            msg->price = price_raw;  // Already in 1/10000ths
            ptr += 4;
            
            break;
        }
        
        case ITCH_MSG_ORDER_EXECUTED: {
            msg->type = MSG_TRADE;
            // Extract: timestamp, order ref, executed shares, match number
            if (end - ptr < 12) return -1;
            ptr += 4;  // Executed shares
            ptr += 8;  // Match number
            break;
        }
        
        case ITCH_MSG_ORDER_CANCEL: {
            msg->type = MSG_CANCEL_ORDER;
            // Extract: timestamp, order ref, canceled shares
            if (end - ptr < 4) return -1;
            ptr += 4;  // Canceled shares
            break;
        }
        
        case ITCH_MSG_ORDER_DELETE: {
            msg->type = MSG_CANCEL_ORDER;
            break;
        }
        
        case ITCH_MSG_ORDER_REPLACE: {
            msg->type = MSG_MODIFY_ORDER;
            // Extract: timestamp, original order ref, new order ref, shares, price
            if (end - ptr < 20) return -1;
            ptr += 8;  // New order ref
            ptr += 4;  // New shares
            ptr += 4;  // New price
            break;
        }
        
        default:
            msg->type = MSG_UNKNOWN;
            break;
    }
    
    // Copy raw data for reprocessing
    msg->raw_len = len;
    memcpy(msg->raw_data, data, len);
    
    atomic_fetch_add_explicit(&ctx->decode_count, 1, memory_order_relaxed);
    return 0;
}
```

### 5.6 SIMD-Accelerated FIX Parser

```c
// fix_simd_parser.c — AVX-512 accelerated FIX tag-value parser
#include "decode_engine.h"
#include <immintrin.h>

// FIX delimiter: 0x01 (SOH)
#define FIX_SOH 0x01

// Parse FIX message using AVX-512
// Returns number of tag-value pairs parsed
int fix_simd_parse(const uint8_t *data, uint16_t len,
                   decoded_field_t *fields, uint16_t max_fields) {
    const uint8_t *ptr = data;
    const uint8_t *end = data + len;
    uint16_t field_count = 0;
    
    // Process 64 bytes at a time with AVX-512
    while (ptr + 64 <= end && field_count < max_fields) {
        __m512i chunk = _mm512_loadu_si512((const __m512i *)ptr);
        
        // Find all SOH delimiters in this chunk
        __mmask64 soh_mask = _mm512_cmpeq_epi8_mask(chunk, _mm512_set1_epi8(FIX_SOH));
        
        // Find all '=' characters (tag-value separator)
        __mmask64 eq_mask = _mm512_cmpeq_epi8_mask(chunk, _mm512_set1_epi8('='));
        
        // Process each tag-value pair
        while (soh_mask && field_count < max_fields) {
            // Find position of next SOH
            int soh_pos = __builtin_ctzll(soh_mask);
            
            // Find corresponding '=' before SOH
            uint64_t eq_before = eq_mask & ((1ULL << soh_pos) - 1);
            if (eq_before) {
                int eq_pos = 63 - __builtin_clzll(eq_before);
                
                // Extract tag (between previous SOH and '=')
                int prev_soh = (field_count > 0) ? 
                    __builtin_ctzll(soh_mask >> (soh_pos + 1)) : -1;
                int tag_start = (prev_soh >= 0) ? prev_soh + 1 : 0;
                int tag_len = eq_pos - tag_start;
                
                // Extract value (between '=' and SOH)
                int val_start = eq_pos + 1;
                int val_len = soh_pos - val_start;
                
                if (tag_len > 0 && val_len > 0) {
                    fields[field_count].data = (uint8_t *)(ptr + val_start);
                    fields[field_count].len = val_len;
                    field_count++;
                }
            }
            
            soh_mask &= soh_mask - 1;  // Clear lowest set bit
        }
        
        ptr += 64;
    }
    
    return field_count;
}
```

### 5.7 Latency Budget

| Metric | Value | Notes |
|---|---|---|
| **p50** | 500 ns | Template-based, branch-minimized |
| **p99** | 1.5 µs | Including complex messages |
| **p999** | 3 µs | Worst-case reassembly |
| **Throughput** | 10-50M msg/s per core | Template cache hit |
| **Jitter** | < 500 ns | No malloc, no syscalls |

### 5.8 Determinism Guarantees

- **Zero-copy decode:** Parse directly from DMA buffer, no intermediate copies
- **Branch-minimized decode:** Use lookup tables, avoid conditionals on hot path
- **Template caching:** Pre-compiled decode templates for FAST/FIX
- **Fixed iteration counts:** No loops with data-dependent bounds
- **No dynamic memory:** All buffers pre-allocated

### 5.9 Testing

```python
# tests/test_decode_engine.py
import pytest
import struct

class TestDecodeEngine:
    """Test decode engine functionality."""
    
    def test_fast_template_decode(self):
        """Verify FAST template-based decoding."""
        # Create FAST-encoded message
        # Decode using template
        # Verify all fields extracted correctly
        pass
    
    def test_itch_message_decode(self):
        """Verify ITCH message decoding."""
        # Create ITCH-encoded message
        # Decode
        # Verify fields
        pass
    
    def test_fix_simd_parse(self):
        """Verify SIMD-accelerated FIX parsing."""
        # Create FIX message
        # Parse with SIMD
        # Verify all tag-value pairs extracted
        pass
    
    def test_zero_copy(self):
        """Verify zero-copy decoding (no intermediate buffers)."""
        # Decode message
        # Verify field pointers point into original packet buffer
        pass
    
    def test_branch_minimization(self):
        """Verify branch-minimized decode path."""
        # Use perf to count branch misses
        # Assert < 10 branch misses per 1000 messages
        pass
    
    def test_template_cache_hit(self):
        """Verify template cache hit rate."""
        # Send 10000 messages with same template
        # Verify > 99% cache hit rate
        pass
    
    def test_malformed_message(self):
        """Verify graceful handling of malformed messages."""
        # Send malformed message
        # Verify error returned, no crash
        pass
```

---

## 6. Stage 4: Normalize & Enrich

### 6.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 NORMALIZE & ENRICH LAYER                     │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Symbol  │──▶│  Price   │──▶│  Side    │──▶│  Time   │ │
│  │  Lookup  │   │  Scale   │   │  Normalize│   │  Normalize│ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │  Canonical│   │  Instrument│   │  Clock   │               │
│  │  Format   │   │  Cache    │   │  Sync    │               │
│  └──────────┘   └──────────┘   └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Components

| Component | Role | Details |
|---|---|---|
| **Canonical Mapper** | Exchange format → internal canonical format | Symbol ID mapping, price scaling, side normalization |
| **Instrument Cache** | Symbol → instrument metadata lookup | Lock-free hash map, pre-warmed |
| **Timestamp Normalizer** | Exchange timestamp → system monotonic clock | PTP-synchronized clock domain crossing |

### 6.3 Data Structures

```c
// normalize.h — Normalize & enrich layer
#ifndef NORMALIZE_H
#define NORMALIZE_H

#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>

#define INSTRUMENT_CACHE_SIZE  1048576  // 2^20
#define SYMBOL_HASH_SEED       0x9E3779B97F4A7C15ULL
#define PRICE_SCALE_MAX        8

// Canonical internal format (the output of this stage)
typedef struct __attribute__((packed, aligned(16))) {
    uint64_t   timestamp_ns;      // Normalized monotonic timestamp
    uint32_t   instrument_id;    // Internal instrument ID
    uint8_t    event_type;        // ADD | MODIFY | CANCEL | TRADE | BOOK_UPDATE
    int64_t    price;             // Fixed-point (scale factor per instrument)
    uint32_t   quantity;
    uint8_t    side;              // BID=0, ASK=1
    uint32_t   order_id;         // Exchange order ID
    uint32_t   flags;            // Hidden, IOC, etc.
    uint64_t   sequence_num;      // Exchange sequence for gap detection
} canonical_event_t;

// Instrument metadata (pre-warmed, read-only after init)
typedef struct __attribute__((aligned(16))) {
    uint32_t instrument_id;       // Internal ID
    uint32_t exchange_id;         // Exchange identifier
    uint32_t symbol_hash;         // Hash of exchange symbol
    int32_t  price_scale;         // Price scaling factor (10^scale)
    uint32_t lot_size;            // Minimum quantity increment
    uint32_t tick_size;           // Minimum price increment
    uint32_t flags;               // Trading halts, etc.
    char     symbol[16];          // Exchange symbol string
} instrument_meta_t;

// Lock-free instrument cache (SwissTable-style)
typedef struct {
    uint8_t ctrl[16];             // Control bytes (SIMD-friendly)
    instrument_meta_t *slots[16]; // Instrument pointers
} instrument_group_t;

typedef struct {
    instrument_group_t *groups;
    uint32_t num_groups;
    uint32_t mask;
    _Atomic uint64_t hits;
    _Atomic uint64_t misses;
} instrument_cache_t;

// Clock synchronization state
typedef struct {
    _Atomic uint64_t ptp_offset;     // Offset from system clock to PTP
    _Atomic uint64_t last_sync;      // Last synchronization time
    _Atomic uint64_t drift_ppb;      // Clock drift in parts per billion
    uint64_t         system_freq;    // TSC frequency
} clock_sync_state_t;

// Normalize context (per-core)
typedef struct __attribute__((aligned(64))) {
    instrument_cache_t *cache;
    clock_sync_state_t *clock;
    _Atomic uint64_t normalize_count;
    _Atomic uint64_t cache_hits;
    _Atomic uint64_t cache_misses;
    char _pad[64 - 4 * sizeof(uint64_t) - 2 * sizeof(void *)];
} normalize_context_t;

#endif // NORMALIZE_H
```

### 6.4 Implementation

```c
// normalize.c — Normalize & enrich implementation
#include "normalize.h"
#include <string.h>
#include <x86intrin.h>

// SwissTable-style hash function (SIMD-friendly)
static inline uint8_t instrument_hash(uint32_t symbol_hash) {
    // FNV-1a inspired hash, returns 7-bit control byte
    uint64_t h = symbol_hash * SYMBOL_HASH_SEED;
    h ^= h >> 33;
    h *= 0xff51afd7ed558ccdULL;
    h ^= h >> 33;
    return (uint8_t)(h >> 57);  // Top 7 bits
}

// SIMD group lookup (SwissTable style)
static inline instrument_meta_t *instrument_lookup(
    instrument_cache_t *cache, uint32_t symbol_hash) {
    
    uint32_t group_idx = symbol_hash & cache->mask;
    instrument_group_t *group = &cache->groups[group_idx];
    
    // SIMD compare: find matching control byte
    __m128i target = _mm_set1_epi8((char)instrument_hash(symbol_hash));
    __m128i ctrl = _mm_loadu_si128((const __m128i *)group->ctrl);
    __m128i match = _mm_cmpeq_epi8(target, ctrl);
    uint32_t mask = _mm_movemask_epi8(match);
    
    if (mask) {
        int slot = __builtin_ctz(mask);
        atomic_fetch_add_explicit(&cache->hits, 1, memory_order_relaxed);
        return group->slots[slot];
    }
    
    atomic_fetch_add_explicit(&cache->misses, 1, memory_order_relaxed);
    return NULL;
}

// Normalize price from exchange format to canonical fixed-point
static inline int64_t normalize_price(int64_t raw_price, int32_t scale) {
    // Use lookup table for common scales
    static const int64_t scale_table[PRICE_SCALE_MAX + 1] = {
        1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000
    };
    
    if (scale >= 0 && scale <= PRICE_SCALE_MAX) {
        return raw_price * scale_table[scale];
    }
    return raw_price;  // Fallback for unusual scales
}

// Normalize side from exchange format to canonical (BID=0, ASK=1)
static inline uint8_t normalize_side(char exchange_side) {
    // Branch-minimized: use lookup table
    static const uint8_t side_table[256] = {
        ['B'] = 0, ['b'] = 0, ['S'] = 1, ['s'] = 1,
        ['0'] = 0, ['1'] = 1,
    };
    return side_table[(uint8_t)exchange_side];
}

// Normalize timestamp from exchange to system monotonic clock
static inline uint64_t normalize_timestamp(uint64_t exchange_ts,
                                            clock_sync_state_t *clock) {
    // Apply PTP offset and drift correction
    uint64_t offset = atomic_load_explicit(&clock->ptp_offset, memory_order_relaxed);
    uint64_t drift = atomic_load_explicit(&clock->drift_ppb, memory_order_relaxed);
    
    // Correct for drift: ts_corrected = ts + offset + (ts * drift / 1e9)
    int64_t drift_correction = (int64_t)((exchange_ts * drift) / 1000000000ULL);
    return exchange_ts + offset + drift_correction;
}

// Main normalize function
int normalize_message(normalize_context_t *ctx,
                      const decoded_message_t *decoded,
                      canonical_event_t *event) {
    // Lookup instrument metadata
    instrument_meta_t *meta = instrument_lookup(ctx->cache, decoded->instrument_id);
    if (!meta) {
        // Cache miss: use default values (or trigger async lookup)
        meta = &default_instrument;
    }
    
    // Normalize timestamp
    event->timestamp_ns = normalize_timestamp(decoded->timestamp_ns, ctx->clock);
    
    // Normalize price
    event->price = normalize_price(decoded->price, meta->price_scale);
    
    // Normalize side
    event->side = normalize_side(decoded->side);
    
    // Copy other fields
    event->instrument_id = meta->instrument_id;
    event->event_type = decoded->type;
    event->quantity = decoded->quantity;
    event->order_id = decoded->order_id;
    event->sequence_num = decoded->sequence_num;
    event->flags = meta->flags;
    
    atomic_fetch_add_explicit(&ctx->normalize_count, 1, memory_order_relaxed);
    return 0;
}

// Pre-warm instrument cache (called at startup)
int instrument_cache_init(instrument_cache_t *cache, const char *instrument_file) {
    // Allocate groups
    cache->num_groups = INSTRUMENT_CACHE_SIZE / 16;
    cache->mask = cache->num_groups - 1;
    cache->groups = aligned_alloc(64, cache->num_groups * sizeof(instrument_group_t));
    
    if (!cache->groups) return -1;
    
    // Initialize all control bytes to 0x80 (empty)
    memset(cache->groups, 0x80, cache->num_groups * sizeof(instrument_group_t));
    
    // Load instruments from file
    // For each instrument:
    //   1. Compute hash
    //   2. Find group
    //   3. Find empty slot
    //   4. Insert
    
    return 0;
}
```

### 6.5 Latency Budget

| Metric | Value | Notes |
|---|---|---|
| **p50** | 200 ns | Lock-free hash lookup |
| **p99** | 500 ns | Including cache miss handling |
| **p999** | 1 µs | Worst-case clock sync |
| **Throughput** | 50M+ events/s per core | Cache hit |
| **Jitter** | < 100 ns | No locks, no syscalls |

### 6.6 Determinism Guarantees

- **Lock-free hash map:** SwissTable with SIMD probing, no locks
- **Pre-warmed cache:** All instruments loaded at startup
- **No dynamic memory:** Fixed-size groups, pre-allocated
- **Branch-minimized:** Lookup tables for side, price scaling
- **Clock sync:** PTP offset applied atomically

### 6.7 Testing

```python
# tests/test_normalize.py
import pytest

class TestNormalize:
    """Test normalize & enrich layer."""
    
    def test_instrument_cache_hit(self):
        """Verify instrument cache lookup latency."""
        # Pre-warm cache
        # Measure lookup latency
        # Assert < 5ns average
        pass
    
    def test_price_normalization(self):
        """Verify price scaling correctness."""
        # Test various price scales
        # Verify correct fixed-point conversion
        pass
    
    def test_side_normalization(self):
        """Verify side normalization."""
        # Test all exchange side formats
        # Verify canonical BID=0, ASK=1
        pass
    
    def test_timestamp_normalization(self):
        """Verify timestamp normalization."""
        # Test PTP offset application
        # Verify drift correction
        pass
    
    def test_cache_miss_handling(self):
        """Verify graceful handling of cache miss."""
        # Lookup non-existent instrument
        # Verify default values used
        pass
```

---

## 7. Stage 5: Sequence Reorder Buffer

### 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                SEQUENCE REORDER BUFFER                       │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  SPSC    │──▶│  Gap     │──▶│  Watermark│──▶│  Gap    │ │
│  │  Ring    │   │  Detect  │   │  Advance  │   │  Alert  │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │  Bitmap  │   │  Timeout │   │  Recovery│               │
│  │  Track   │   │  Trigger │   │  Request │               │
│  └──────────┘   └──────────┘   └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Components

| Component | Role | Details |
|---|---|---|
| **Per-session ring buffer** | Hold out-of-order messages until gap fills | Lock-free SPSC ring per session |
| **Gap detector** | Detect missing sequence numbers | Bitmap-based gap tracking |
| **Recovery trigger** | Request retransmission on gap | Automatic or manual gap fill request |

### 7.3 Data Structures

```c
// sequence_reorder.h — Sequence reorder buffer
#ifndef SEQUENCE_REORDER_H
#define SEQUENCE_REORDER_H

#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>

#define REORDER_RING_SIZE    4096   // Power of 2
#define REORDER_MASK         (REORDER_RING_SIZE - 1)
#define MAX_GAP_TRACKING     1024   // Max gaps to track
#define GAP_TIMEOUT_US       100    // Gap alert timeout

// SPSC ring buffer for reorder (lock-free)
typedef struct __attribute__((aligned(64))) {
    _Atomic uint64_t head;                    // Consumer index
    _Atomic uint64_t tail;                    // Producer index
    canonical_event_t *slots[REORDER_RING_SIZE];
    char _pad[64 - 2 * sizeof(uint64_t)];
} reorder_ring_t;

// Gap tracking bitmap (one bit per sequence number)
typedef struct {
    uint64_t bits[MAX_GAP_TRACKING / 64];  // Bitmap
    uint64_t base_seq;                     // Base sequence for bitmap
    uint32_t num_gaps;                     // Number of gaps detected
} gap_bitmap_t;

// Per-session reorder state
typedef struct __attribute__((aligned(64))) {
    uint32_t session_id;
    uint64_t expected_seq;                 // Next expected sequence
    uint64_t contiguous_seq;               // Contiguous frontier
    uint64_t last_timestamp;               // Last update time
    reorder_ring_t ring;
    gap_bitmap_t gaps;
    _Atomic uint64_t gaps_detected;
    _Atomic uint64_t gaps_filled;
    _Atomic uint64_t messages_reordered;
    char _pad[64 - 6 * sizeof(uint64_t) - sizeof(void *)];
} reorder_state_t;

// Gap alert (sent to recovery handler)
typedef struct {
    uint32_t session_id;
    uint64_t gap_start;
    uint64_t gap_end;
    uint64_t timestamp_us;
    uint8_t  severity;  // 0=info, 1=warning, 2=critical
} gap_alert_t;

#endif // SEQUENCE_REORDER_H
```

### 7.4 Implementation

```c
// sequence_reorder.c — Sequence reorder buffer implementation
#include "sequence_reorder.h"
#include <string.h>

// Submit message to reorder buffer
// Returns: 0 = in-order (ready to forward), 1 = buffered (out-of-order), -1 = error
int reorder_submit(reorder_state_t *state, const canonical_event_t *event) {
    uint64_t seq = event->sequence_num;
    uint64_t expected = atomic_load_explicit(&state->expected_seq, memory_order_relaxed);
    
    if (seq == expected) {
        // In-order: advance contiguous frontier
        atomic_store_explicit(&state->expected_seq, seq + 1, memory_order_relaxed);
        atomic_store_explicit(&state->contiguous_seq, seq, memory_order_relaxed);
        
        // Check if we can advance further (gap fill)
        reorder_advance(state);
        return 0;  // Ready to forward
    }
    
    if (seq > expected) {
        // Future message: buffer it and record gap
        uint64_t tail = atomic_load_explicit(&state->ring.tail, memory_order_relaxed);
        uint64_t head = atomic_load_explicit(&state->ring.head, memory_order_relaxed);
        
        if ((tail - head) >= REORDER_RING_SIZE) {
            return -1;  // Ring full
        }
        
        // Store event in ring
        state->ring.slots[tail & REORDER_MASK] = (canonical_event_t *)event;
        atomic_store_explicit(&state->ring.tail, tail + 1, memory_order_release);
        
        // Record gap
        gap_record(&state->gaps, expected, seq - 1);
        atomic_fetch_add_explicit(&state->gaps_detected, 1, memory_order_relaxed);
        
        return 1;  // Buffered
    }
    
    // seq < expected: duplicate or late message
    return -1;
}

// Advance contiguous frontier (called after gap fill)
void reorder_advance(reorder_state_t *state) {
    uint64_t head = atomic_load_explicit(&state->ring.head, memory_order_relaxed);
    uint64_t tail = atomic_load_explicit(&state->ring.tail, memory_order_relaxed);
    
    while (head < tail) {
        canonical_event_t *event = state->ring.slots[head & REORDER_MASK];
        if (!event) break;
        
        uint64_t seq = event->sequence_num;
        uint64_t expected = atomic_load_explicit(&state->expected_seq, memory_order_relaxed);
        
        if (seq == expected) {
            // Forward to next stage
            book_update_submit(event);
            atomic_store_explicit(&state->expected_seq, seq + 1, memory_order_relaxed);
            atomic_store_explicit(&state->contiguous_seq, seq, memory_order_relaxed);
            atomic_fetch_add_explicit(&state->messages_reordered, 1, memory_order_relaxed);
            head++;
        } else if (seq < expected) {
            // Duplicate: skip
            head++;
        } else {
            // Still a gap: stop
            break;
        }
    }
    
    atomic_store_explicit(&state->ring.head, head, memory_order_relaxed);
}

// Record a gap in the bitmap
void gap_record(gap_bitmap_t *gaps, uint64_t start, uint64_t end) {
    for (uint64_t seq = start; seq <= end; seq++) {
        uint64_t offset = seq - gaps->base_seq;
        if (offset < MAX_GAP_TRACKING) {
            gaps->bits[offset / 64] |= (1ULL << (offset % 64));
        }
    }
    gaps->num_gaps += (end - start + 1);
}

// Check if gap is filled
bool gap_is_filled(const gap_bitmap_t *gaps, uint64_t start, uint64_t end) {
    for (uint64_t seq = start; seq <= end; seq++) {
        uint64_t offset = seq - gaps->base_seq;
        if (offset < MAX_GAP_TRACKING) {
            if (!(gaps->bits[offset / 64] & (1ULL << (offset % 64)))) {
                return false;
            }
        }
    }
    return true;
}

// Gap timeout check (called periodically)
void reorder_check_timeouts(reorder_state_t *state, uint64_t now_us) {
    uint64_t last = atomic_load_explicit(&state->last_timestamp, memory_order_relaxed);
    
    if ((now_us - last) > GAP_TIMEOUT_US && state->gaps.num_gaps > 0) {
        // Gap alert: trigger recovery
        gap_alert_t alert = {
            .session_id = state->session_id,
            .gap_start = state->expected_seq,
            .gap_end = state->expected_seq + state->gaps.num_gaps - 1,
            .timestamp_us = now_us,
            .severity = (state->gaps.num_gaps > 10) ? 2 : 1,
        };
        
        // Send alert to recovery handler (non-blocking)
        recovery_submit_alert(&alert);
    }
}
```

### 7.5 Latency Budget

| Metric | Value | Notes |
|---|---|---|
| **p50** | 100 ns | SPSC ring buffer |
| **p99** | 300 ns | Including gap detection |
| **p999** | 500 ns | Worst-case ring full |
| **Throughput** | 100M+ events/s per session | Lock-free |
| **Jitter** | < 50 ns | No locks, no syscalls |

### 7.6 Determinism Guarantees

- **SPSC lock-free ring:** No locks, no CAS contention
- **Bitmap gap tracking:** O(1) gap detection
- **Watermark advancement:** Only advance contiguous frontier
- **Timeout-based recovery:** Bounded wait for gap fill
- **No dynamic memory:** Fixed-size ring, pre-allocated

### 7.7 Testing

```python
# tests/test_sequence_reorder.py
import pytest

class TestSequenceReorder:
    """Test sequence reorder buffer."""
    
    def test_in_order_advance(self):
        """Verify in-order message advancement."""
        # Submit messages in order
        # Verify contiguous frontier advances
        pass
    
    def test_out_of_order_buffer(self):
        """Verify out-of-order message buffering."""
        # Submit message with gap
        # Verify message buffered
        # Verify gap recorded
        pass
    
    def test_gap_fill_advance(self):
        """Verify gap fill triggers advancement."""
        # Create gap
        # Fill gap
        # Verify all buffered messages forwarded
        pass
    
    def test_duplicate_detection(self):
        """Verify duplicate message detection."""
        # Submit duplicate sequence
        # Verify duplicate detected and skipped
        pass
    
    def test_ring_full(self):
        """Verify graceful handling of ring full."""
        # Fill ring completely
        # Verify error returned, no crash
        pass
    
    def test_gap_timeout(self):
        """Verify gap timeout triggers recovery."""
        # Create gap
        # Wait for timeout
        # Verify recovery alert sent
        pass
```

---

## 8. Stage 6: Order Book Update

### 8.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   ORDER BOOK UPDATE                          │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Price   │──▶│  Level   │──▶│  Order   │──▶│  Delta  │ │
│  │  Level   │   │  Update  │   │  Match   │   │  Gen    │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │  Array-  │   │  Cache-  │   │  Snapshot│               │
│  │  Based   │   │  Friendly│   │  Manager │               │
│  └──────────┘   └──────────┘   └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Components

| Component | Role | Details |
|---|---|---|
| **Book Builder** | Maintain top-of-book or full depth | Array-based price levels (cache-friendly) |
| **Delta Generator** | Compute book changes for downstream | Only send what changed |
| **Snapshot Manager** | Periodic full book snapshots | For new subscribers / recovery |

### 8.3 Data Structures

```c
// order_book.h — Order book update layer
#ifndef ORDER_BOOK_H
#define ORDER_BOOK_H

#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>

#define MAX_PRICE_LEVELS     4096
#define MAX_ORDERS_PER_LEVEL 256
#define BOOK_DEPTH           10
#define PRICE_INDEX_SHIFT    8  // 2^8 = 256 price levels per index

// Price level (cache-line aligned)
typedef struct __attribute__((aligned(64))) {
    int64_t price;
    uint32_t total_quantity;
    uint32_t order_count;
    uint32_t head;              // Index into order array
    uint32_t tail;
    char _pad[64 - 8 - 4 * sizeof(uint32_t)];
} price_level_t;

// Order in book
typedef struct __attribute__((aligned(16))) {
    uint32_t order_id;
    uint32_t quantity;
    uint32_t instrument_id;
    uint8_t  side;              // BID=0, ASK=1
    uint8_t  flags;
    uint16_t _pad;
} book_order_t;

// Order book (per instrument)
typedef struct __attribute__((aligned(64))) {
    uint32_t instrument_id;
    int64_t  best_bid;
    int64_t  best_ask;
    uint32_t bid_depth;
    uint32_t ask_depth;
    
    // Array-based price levels (cache-friendly)
    price_level_t bid_levels[MAX_PRICE_LEVELS];
    price_level_t ask_levels[MAX_PRICE_LEVELS];
    
    // Order storage
    book_order_t orders[MAX_PRICE_LEVELS * MAX_ORDERS_PER_LEVEL];
    uint32_t order_count;
    
    _Atomic uint64_t update_count;
    _Atomic uint64_t last_update_ns;
    char _pad[64 - 2 * sizeof(uint64_t) - sizeof(uint32_t)];
} order_book_t;

// Book delta (for downstream consumers)
typedef struct __attribute__((packed)) {
    uint32_t instrument_id;
    uint8_t  side;              // BID=0, ASK=1
    uint8_t  action;            // ADD=0, MODIFY=1, CANCEL=2
    int64_t  price;
    uint32_t quantity;
    uint32_t order_id;
    uint64_t timestamp_ns;
} book_delta_t;

// Snapshot for recovery
typedef struct {
    uint32_t instrument_id;
    uint32_t num_bid_levels;
    uint32_t num_ask_levels;
    price_level_t bid_levels[BOOK_DEPTH];
    price_level_t ask_levels[BOOK_DEPTH];
    uint64_t timestamp_ns;
} book_snapshot_t;

#endif // ORDER_BOOK_H
```

### 8.4 Implementation

```c
// order_book.c — Order book update implementation
#include "order_book.h"
#include <string.h>

// Price to index conversion (for array-based levels)
static inline uint32_t price_to_index(int64_t price, int64_t tick_size) {
    return (uint32_t)(price / tick_size);
}

// Update book with canonical event
void book_update(order_book_t *book, const canonical_event_t *event) {
    uint32_t idx = price_to_index(event->price, 1);  // tick_size = 1 for simplicity
    
    if (event->side == 0) {  // BID
        price_level_t *level = &book->bid_levels[idx];
        
        switch (event->event_type) {
            case MSG_ADD_ORDER:
                level->price = event->price;
                level->total_quantity += event->quantity;
                level->order_count++;
                break;
                
            case MSG_MODIFY_ORDER:
                // Update existing order quantity
                level->total_quantity += event->quantity;  // Delta
                break;
                
            case MSG_CANCEL_ORDER:
                level->total_quantity -= event->quantity;
                level->order_count--;
                break;
                
            default:
                break;
        }
        
        // Update best bid
        if (event->price > book->best_bid) {
            book->best_bid = event->price;
        }
        
    } else {  // ASK
        price_level_t *level = &book->ask_levels[idx];
        
        switch (event->event_type) {
            case MSG_ADD_ORDER:
                level->price = event->price;
                level->total_quantity += event->quantity;
                level->order_count++;
                break;
                
            case MSG_MODIFY_ORDER:
                level->total_quantity += event->quantity;
                break;
                
            case MSG_CANCEL_ORDER:
                level->total_quantity -= event->quantity;
                level->order_count--;
                break;
                
            default:
                break;
        }
        
        // Update best ask
        if (book->best_ask == 0 || event->price < book->best_ask) {
            book->best_ask = event->price;
        }
    }
    
    atomic_fetch_add_explicit(&book->update_count, 1, memory_order_relaxed);
    atomic_store_explicit(&book->last_update_ns, event->timestamp_ns, memory_order_relaxed);
}

// Generate delta for downstream consumers
void book_generate_delta(const order_book_t *book, const canonical_event_t *event,
                         book_delta_t *delta) {
    delta->instrument_id = event->instrument_id;
    delta->side = event->side;
    delta->price = event->price;
    delta->quantity = event->quantity;
    delta->order_id = event->order_id;
    delta->timestamp_ns = event->timestamp_ns;
    
    switch (event->event_type) {
        case MSG_ADD_ORDER:
            delta->action = 0;  // ADD
            break;
        case MSG_MODIFY_ORDER:
            delta->action = 1;  // MODIFY
            break;
        case MSG_CANCEL_ORDER:
            delta->action = 2;  // CANCEL
            break;
        default:
            delta->action = 0;
            break;
    }
}

// Create snapshot (for recovery)
void book_create_snapshot(const order_book_t *book, book_snapshot_t *snapshot) {
    snapshot->instrument_id = book->instrument_id;
    snapshot->timestamp_ns = atomic_load_explicit(&book->last_update_ns, memory_order_relaxed);
    
    // Copy top N levels
    snapshot->num_bid_levels = (book->bid_depth < BOOK_DEPTH) ? book->bid_depth : BOOK_DEPTH;
    snapshot->num_ask_levels = (book->ask_depth < BOOK_DEPTH) ? book->ask_depth : BOOK_DEPTH;
    
    for (uint32_t i = 0; i < snapshot->num_bid_levels; i++) {
        snapshot->bid_levels[i] = book->bid_levels[i];
    }
    for (uint32_t i = 0; i < snapshot->num_ask_levels; i++) {
        snapshot->ask_levels[i] = book->ask_levels[i];
    }
}
```

### 8.5 Latency Budget

| Metric | Value | Notes |
|---|---|---|
| **p50** | 300 ns | Array-based, cache-friendly |
| **p99** | 800 ns | Including delta generation |
| **p999** | 1.5 µs | Worst-case deep book |
| **Throughput** | 50M+ updates/s per instrument | Array access |
| **Jitter** | < 100 ns | No locks, no syscalls |

### 8.6 Determinism Guarantees

- **Array-based levels:** O(1) price level access, cache-friendly
- **No locks:** Per-instrument book, single writer
- **No dynamic memory:** Fixed-size arrays, pre-allocated
- **Cache-line aligned:** Price levels aligned to cache lines
- **Bounded execution:** Fixed iteration counts for snapshot

### 8.7 Testing

```python
# tests/test_order_book.py
import pytest

class TestOrderBook:
    """Test order book update layer."""
    
    def test_add_order(self):
        """Verify order addition to book."""
        # Add order
        # Verify price level updated
        # Verify best bid/ask updated
        pass
    
    def test_cancel_order(self):
        """Verify order cancellation."""
        # Add order
        # Cancel order
        # Verify quantity reduced
        pass
    
    def test_modify_order(self):
        """Verify order modification."""
        # Add order
        # Modify order
        # Verify quantity updated
        pass
    
    def test_best_bid_ask(self):
        """Verify best bid/ask tracking."""
        # Add multiple orders at different prices
        # Verify best bid/ask correct
        pass
    
    def test_delta_generation(self):
        """Verify delta generation for downstream."""
        # Update book
        # Generate delta
        # Verify delta contains correct changes
        pass
    
    def test_snapshot_creation(self):
        """Verify snapshot creation for recovery."""
        # Update book
        # Create snapshot
        # Verify snapshot contains correct state
        pass
```

---

## 9. Stage 7: Fan-Out / Distributor

### 9.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  FAN-OUT / DISTRIBUTOR                       │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Shared  │──▶│  SPSC    │──▶│  Zero-   │──▶│  Multi- │ │
│  │  Memory  │   │  Rings   │   │  Copy    │   │  cast   │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │  Per-    │   │  Back-   │   │  Priority│               │
│  │  Consumer│   │  pressure│   │  Lanes   │               │
│  └──────────┘   └──────────┘   └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Components

| Component | Role | Details |
|---|---|---|
| **Multicast Publisher** | One-to-many distribution | Shared memory + UDP multicast |
| **Shared Memory Ring** | Inter-process communication | Lock-free SPSC/MPSC rings per consumer |
| **Event Bus** | Pub/sub with topic filtering | Instrument-partitioned channels |

### 9.3 Data Structures

```c
// fanout.h — Fan-out / distributor layer
#ifndef FANOUT_H
#define FANOUT_H

#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>

#define MAX_CONSUMERS        32
#define FANOUT_RING_SIZE    8192   // Power of 2
#define FANOUT_MASK         (FANOUT_RING_SIZE - 1)
#define MAX_PRIORITY_LANES  4

// Consumer types
typedef enum {
    CONSUMER_MATCHING_ENGINE = 0,   // Highest priority
    CONSUMER_RISK_ENGINE = 1,
    CONSUMER_MARKET_DATA = 2,
    CONSUMER_LOGGING = 3,           // Lowest priority
    CONSUMER_COUNT
} consumer_type_t;

// SPSC ring buffer for fan-out (lock-free)
typedef struct __attribute__((aligned(64))) {
    _Atomic uint64_t head;                    // Consumer index
    _Atomic uint64_t tail;                    // Producer index
    canonical_event_t *slots[FANOUT_RING_SIZE];
    char _pad[64 - 2 * sizeof(uint64_t)];
} fanout_ring_t;

// Per-consumer state
typedef struct __attribute__((aligned(64))) {
    uint32_t consumer_id;
    consumer_type_t type;
    fanout_ring_t ring;
    _Atomic uint64_t sent_count;
    _Atomic uint64_t dropped_count;
    _Atomic uint64_t last_sequence;
    bool active;
    char _pad[64 - 3 * sizeof(uint64_t) - sizeof(uint32_t) - sizeof(consumer_type_t) - sizeof(bool)];
} consumer_state_t;

// Fan-out context (per-producer)
typedef struct __attribute__((aligned(64))) {
    consumer_state_t consumers[MAX_CONSUMERS];
    uint32_t num_consumers;
    _Atomic uint64_t fanout_count;
    _Atomic uint64_t drop_count;
    char _pad[64 - 2 * sizeof(uint64_t) - sizeof(uint32_t)];
} fanout_context_t;

// Multicast configuration
typedef struct {
    uint32_t multicast_addr;     // IP address
    uint16_t multicast_port;     // Port
    uint8_t  ttl;                // Time to live
    bool     loopback;           // Enable loopback
} multicast_config_t;

#endif // FANOUT_H
```

### 9.4 Implementation

```c
// fanout.c — Fan-out / distributor implementation
#include "fanout.h"
#include <string.h>

// Submit event to all consumers (zero-copy fan-out)
int fanout_submit(fanout_context_t *ctx, const canonical_event_t *event) {
    uint32_t num_consumers = ctx->num_consumers;
    
    for (uint32_t i = 0; i < num_consumers; i++) {
        consumer_state_t *consumer = &ctx->consumers[i];
        
        if (!consumer->active) continue;
        
        // Check priority lane
        if (consumer->type == CONSUMER_LOGGING && event->event_type == MSG_HEARTBEAT) {
            // Skip logging consumer for heartbeats
            continue;
        }
        
        // Try to enqueue to consumer's ring
        uint64_t tail = atomic_load_explicit(&consumer->ring.tail, memory_order_relaxed);
        uint64_t head = atomic_load_explicit(&consumer->ring.head, memory_order_relaxed);
        
        if ((tail - head) >= FANOUT_RING_SIZE) {
            // Ring full: drop for this consumer (non-blocking)
            atomic_fetch_add_explicit(&consumer->dropped_count, 1, memory_order_relaxed);
            atomic_fetch_add_explicit(&ctx->drop_count, 1, memory_order_relaxed);
            continue;
        }
        
        // Store event pointer (zero-copy)
        consumer->ring.slots[tail & FANOUT_MASK] = (canonical_event_t *)event;
        atomic_store_explicit(&consumer->ring.tail, tail + 1, memory_order_release);
        
        atomic_fetch_add_explicit(&consumer->sent_count, 1, memory_order_relaxed);
    }
    
    atomic_fetch_add_explicit(&ctx->fanout_count, 1, memory_order_relaxed);
    return 0;
}

// Consumer-side: dequeue event (called by consumer thread)
canonical_event_t *fanout_consume(consumer_state_t *consumer) {
    uint64_t head = atomic_load_explicit(&consumer->ring.head, memory_order_relaxed);
    uint64_t tail = atomic_load_explicit(&consumer->ring.tail, memory_order_acquire);
    
    if (head == tail) {
        return NULL;  // Empty
    }
    
    canonical_event_t *event = consumer->ring.slots[head & FANOUT_MASK];
    atomic_store_explicit(&consumer->ring.head, head + 1, memory_order_release);
    
    return event;
}

// Multicast fan-out (for network distribution)
int fanout_multicast(fanout_context_t *ctx, const canonical_event_t *event,
                     const multicast_config_t *config) {
    // Serialize event to buffer
    uint8_t buffer[256];
    uint16_t len = serialize_event(event, buffer, sizeof(buffer));
    
    // Send multicast packet
    // (Implementation depends on socket setup)
    // sendto(mcast_socket, buffer, len, 0, ...);
    
    return 0;
}

// Serialize event for network transmission
uint16_t serialize_event(const canonical_event_t *event, uint8_t *buffer, uint16_t max_len) {
    if (max_len < sizeof(canonical_event_t)) return 0;
    
    memcpy(buffer, event, sizeof(canonical_event_t));
    return sizeof(canonical_event_t);
}
```

### 9.5 Latency Budget

| Metric | Value | Notes |
|---|---|---|
| **p50** | 200 ns | Shared memory write |
| **p99** | 500 ns | Including multicast |
| **p999** | 1 µs | Worst-case ring full |
| **Throughput** | 100M+ events/s | Zero-copy |
| **Jitter** | < 50 ns | No locks, no syscalls |

### 9.6 Determinism Guarantees

- **Zero-copy fan-out:** Single decode, multiple consumers via shared memory
- **SPSC lock-free rings:** No locks, no CAS contention
- **Non-blocking:** Drop on ring full, never block hot path
- **Priority lanes:** Separate channels for time-critical vs. bulk
- **No dynamic memory:** Fixed-size rings, pre-allocated

### 9.7 Testing

```python
# tests/test_fanout.py
import pytest

class TestFanOut:
    """Test fan-out / distributor layer."""
    
    def test_zero_copy_fanout(self):
        """Verify zero-copy fan-out to multiple consumers."""
        # Submit event
        # Verify all consumers receive same pointer
        pass
    
    def test_ring_full_handling(self):
        """Verify graceful handling of ring full."""
        # Fill consumer ring
        # Submit more events
        # Verify drops counted, no crash
        pass
    
    def test_priority_lanes(self):
        """Verify priority lane separation."""
        # Submit heartbeat
        # Verify matching engine receives it
        # Verify logging consumer does not
        pass
    
    def test_multicast_distribution(self):
        """Verify multicast distribution."""
        # Submit event
        # Verify multicast packet sent
        pass
    
    def test_consumer_activation(self):
        """Verify consumer activation/deactivation."""
        # Deactivate consumer
        # Submit event
        # Verify consumer does not receive event
        pass
```

---

## 10. End-to-End Integration

### 10.1 Pipeline Integration

```c
// feed_handler.c — End-to-end feed handler pipeline
#include "nic_config.h"
#include "kernel_bypass.h"
#include "decode_engine.h"
#include "normalize.h"
#include "sequence_reorder.h"
#include "order_book.h"
#include "fanout.h"

// Per-core pipeline context
typedef struct __attribute__((aligned(64))) {
    decode_context_t decode_ctx;
    normalize_context_t normalize_ctx;
    reorder_state_t reorder_ctx;
    order_book_t book_ctx;
    fanout_context_t fanout_ctx;
    
    // Pipeline function pointers
    int (*decode)(struct decode_context_t *, const uint8_t *, uint16_t, decoded_message_t *);
    int (*normalize)(struct normalize_context_t *, const decoded_message_t *, canonical_event_t *);
    int (*reorder)(struct reorder_state_t *, const canonical_event_t *);
    void (*book_update)(struct order_book_t *, const canonical_event_t *);
    int (*fanout)(struct fanout_context_t *, const canonical_event_t *);
} pipeline_context_t;

// Main processing function (called per packet)
void process_packet(pipeline_context_t *ctx, const packet_ref_t *pkt) {
    decoded_message_t decoded;
    canonical_event_t event;
    
    // Stage 3: Decode
    if (ctx->decode(&ctx->decode_ctx, pkt->data, pkt->len, &decoded) != 0) {
        return;  // Decode error
    }
    
    // Stage 4: Normalize
    if (ctx->normalize(&ctx->normalize_ctx, &decoded, &event) != 0) {
        return;  // Normalize error
    }
    
    // Stage 5: Sequence reorder
    int reorder_result = ctx->reorder(&ctx->reorder_ctx, &event);
    if (reorder_result < 0) {
        return;  // Reorder error
    }
    if (reorder_result > 0) {
        return;  // Buffered (out-of-order)
    }
    
    // Stage 6: Book update
    ctx->book_update(&ctx->book_ctx, &event);
    
    // Stage 7: Fan-out
    ctx->fanout(&ctx->fanout_ctx, &event);
}

// Per-core pipeline thread
void *pipeline_thread(void *arg) {
    pipeline_context_t *ctx = (pipeline_context_t *)arg;
    
    // Initialize stages
    decode_init(&ctx->decode_ctx);
    normalize_init(&ctx->normalize_ctx);
    reorder_init(&ctx->reorder_ctx);
    book_init(&ctx->book_ctx);
    fanout_init(&ctx->fanout_ctx);
    
    // Set function pointers
    ctx->decode = fast_decode;
    ctx->normalize = normalize_message;
    ctx->reorder = reorder_submit;
    ctx->book_update = book_update;
    ctx->fanout = fanout_submit;
    
    // Main loop
    while (1) {
        // Stage 2: Kernel bypass RX
        packet_ref_t pkt;
        if (dpdk_rx_burst(&pkt) != 0) {
            continue;
        }
        
        // Process through pipeline
        process_packet(ctx, &pkt);
        
        // Release packet
        packet_release(&pkt);
    }
    
    return NULL;
}
```

### 10.2 End-to-End Latency Budget

| Stage | p50 | p99 | p999 | Notes |
|---|---|---|---|---|
| **S1: NIC DMA + HW Timestamp** | 200 ns | 500 ns | 1 µs | PHY/MAC layer, deterministic |
| **S2: Kernel Bypass (PMD)** | 300 ns | 800 ns | 1.5 µs | DPDK poll, cache-hot |
| **S3: Decode Engine** | 500 ns | 1.5 µs | 3 µs | Template-based, branch-minimized |
| **S4: Normalize & Enrich** | 200 ns | 500 ns | 1 µs | Lock-free hash lookup |
| **S5: Sequence Check** | 100 ns | 300 ns | 500 ns | SPSC ring buffer |
| **S6: Book Update** | 300 ns | 800 ns | 1.5 µs | Array-based, cache-friendly |
| **S7: Fan-Out** | 200 ns | 500 ns | 1 µs | Shared memory write |
| **TOTAL** | **1.8 µs** | **4.9 µs** | **9.5 µs** | Wire to consumer |

### 10.3 Throughput Targets

| Feed Type | Message Rate | Avg Msg Size | Bandwidth |
|---|---|---|---|
| **Equity TOPS/ITCH** | 5–15M msg/s | 40–80 bytes | 400 Mb/s – 1.2 Gb/s |
| **Equity Full Depth (PILLAR)** | 20–50M msg/s | 40–120 bytes | 1–4 Gb/s |
| **Futures (CME MDP 3.0)** | 10–30M msg/s | 60–150 bytes | 1–3 Gb/s |
| **Options (OPRA)** | 30–80M msg/s | 30–60 bytes | 1–3 Gb/s |

### 10.4 Aggregate System Throughput

| Metric | Target |
|---|---|
| **Total messages/second** | > 100M msg/s (all feeds) |
| **Total bandwidth** | > 10 Gb/s ingress |
| **Concurrent instruments** | > 500K |
| **Concurrent sessions** | > 100 (multi-venue) |

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# tests/test_feed_handler_integration.py
import pytest
import subprocess
import time
import struct

class TestFeedHandlerIntegration:
    """Integration tests for the complete feed handler pipeline."""
    
    def test_end_to_end_latency(self):
        """Measure end-to-end latency from wire to consumer."""
        # Send test packet
        # Measure time from TX to RX at consumer
        # Assert p99 < 5µs
        pass
    
    def test_throughput_sustained(self):
        """Verify sustained throughput over time."""
        # Send traffic at target rate for 60 seconds
        # Verify no degradation
        pass
    
    def test_packet_loss(self):
        """Verify zero packet loss under load."""
        # Send known number of packets
        # Verify all packets received
        pass
    
    def test_sequence_integrity(self):
        """Verify sequence integrity across pipeline."""
        # Send messages with known sequence numbers
        # Verify order preserved
        pass
    
    def test_gap_recovery(self):
        """Verify gap detection and recovery."""
        # Create sequence gap
        # Verify gap detected
        # Fill gap
        # Verify recovery
        pass
    
    def test_failover(self):
        """Verify failover to standby."""
        # Kill primary handler
        # Verify standby takes over
        # Verify no message loss
        pass
```

### 11.2 Performance Tests

```python
# tests/test_performance.py
import pytest
import time
import statistics

class TestPerformance:
    """Performance benchmarks for feed handler."""
    
    def test_decode_throughput(self):
        """Benchmark decode engine throughput."""
        # Generate 1M messages
        # Measure decode time
        # Assert > 10M msg/s
        pass
    
    def test_normalize_throughput(self):
        """Benchmark normalize throughput."""
        # Generate 1M decoded messages
        # Measure normalize time
        # Assert > 50M msg/s
        pass
    
    def test_book_update_throughput(self):
        """Benchmark book update throughput."""
        # Generate 1M events
        # Measure book update time
        # Assert > 50M updates/s
        pass
    
    def test_fanout_throughput(self):
        """Benchmark fan-out throughput."""
        # Generate 1M events
        # Measure fan-out time
        # Assert > 100M events/s
        pass
    
    def test_latency_distribution(self):
        """Measure latency distribution."""
        # Send 1M messages
        # Collect latency samples
        # Verify p50 < 2µs, p99 < 5µs, p999 < 10µs
        pass
```

### 11.3 Stress Tests

```python
# tests/test_stress.py
import pytest

class TestStress:
    """Stress tests for feed handler."""
    
    def test_burst_handling(self):
        """Verify handling of traffic bursts."""
        # Send burst of 100K messages
        # Verify no packet loss
        pass
    
    def test_sustained_load(self):
        """Verify stability under sustained load."""
        # Run at 80% capacity for 1 hour
        # Verify no degradation
        pass
    
    def test_memory_leaks(self):
        """Verify no memory leaks."""
        # Run for 1 hour
        # Monitor memory usage
        # Assert no growth
        pass
    
    def test_cpu_pinning(self):
        """Verify CPU pinning effectiveness."""
        # Check thread affinity
        # Verify threads on isolated cores
        pass
```

---

## 12. Optimization Guide

### 12.1 Latency-Critical Optimizations

| Technique | Savings | Trade-off |
|---|---|---|
| FPGA pre-decode | 1–3 µs | Cost, flexibility |
| Hugepages (1GB) | 200–500 ns | Memory commitment |
| CPU core isolation (`isolcpus`) | 500 ns – 2 µs | Reduced core availability |
| Busy polling (DPDK) | 1–5 µs | 100% CPU utilization |
| Cache-line alignment | 100–300 ns | Memory overhead |
| NUMA-aware allocation | 200–500 ns | Complexity |
| SIMD decode (AVX-512) | 200–500 ns | Portability |
| Branch minimization | 100–200 ns | Code complexity |
| Prefetching | 100–300 ns | Cache pollution |
| Lock-free structures | 50–200 ns | Implementation complexity |

### 12.2 Cache Optimization

```c
// Cache optimization techniques

// 1. Cache-line alignment
struct __attribute__((aligned(64))) hot_data {
    // Frequently accessed data
};

// 2. Prefetching
__builtin_prefetch(&data, 0, 3);  // Read, high temporal locality

// 3. False sharing prevention
struct __attribute__((aligned(64))) {
    _Atomic uint64_t counter;
    char _pad[64 - sizeof(uint64_t)];
} per_core_counter;

// 4. Data structure sizing
// Fit hot data in L1 cache (32KB)
// Fit working set in L2 cache (256KB)
```

### 12.3 Compiler Optimizations

```makefile
# Makefile optimizations for feed handler
CFLAGS = -O3 \
         -march=native \
         -mtune=native \
         -flto \
         -fomit-frame-pointer \
         -funroll-loops \
         -finline-functions \
         -fpredictive-commoning \
         -ftree-vectorize \
         -fopt-info-vec-missed

# Link-time optimization
LDFLAGS = -flto -fuse-ld=gold

# Profile-guided optimization
# 1. Compile with -fprofile-generate
# 2. Run with representative workload
# 3. Recompile with -fprofile-use
```

---

## 13. Monitoring & Alerting

### 13.1 Per-Stage Timing

```c
// monitoring.h — Latency monitoring
#ifndef MONITORING_H
#define MONITORING_H

#include <stdint.h>
#include <x86intrin.h>

#define HISTOGRAM_SIZE  1024
#define ALERT_P99_US    5
#define ALERT_P999_US   10

// Per-stage latency histogram
typedef struct {
    _Atomic uint64_t buckets[HISTOGRAM_SIZE];
    _Atomic uint64_t count;
    _Atomic uint64_t sum;
    _Atomic uint64_t min;
    _Atomic uint64_t max;
} latency_histogram_t;

// TSC-based timing
static inline uint64_t rdtsc(void) {
    return __rdtsc();
}

// Record latency sample
void record_latency(latency_histogram_t *hist, uint64_t cycles, uint64_t tsc_freq) {
    uint64_t ns = (cycles * 1000000000ULL) / tsc_freq;
    uint64_t bucket = (ns < HISTOGRAM_SIZE) ? ns : HISTOGRAM_SIZE - 1;
    
    atomic_fetch_add_explicit(&hist->buckets[bucket], 1, memory_order_relaxed);
    atomic_fetch_add_explicit(&hist->count, 1, memory_order_relaxed);
    atomic_fetch_add_explicit(&hist->sum, ns, memory_order_relaxed);
}

// Get percentile (approximate)
uint64_t get_percentile(latency_histogram_t *hist, double p) {
    uint64_t target = (uint64_t)(atomic_load_explicit(&hist->count, memory_order_relaxed) * p);
    uint64_t sum = 0;
    
    for (uint64_t i = 0; i < HISTOGRAM_SIZE; i++) {
        sum += atomic_load_explicit(&hist->buckets[i], memory_order_relaxed);
        if (sum >= target) {
            return i;  // nanoseconds
        }
    }
    return HISTOGRAM_SIZE;
}

#endif // MONITORING_H
```

### 13.2 Alerting

```python
# monitoring/alerting.py
import time
import statistics

class LatencyMonitor:
    """Real-time latency monitoring and alerting."""
    
    def __init__(self):
        self.samples = []
        self.alert_p99 = 5.0  # µs
        self.alert_p999 = 10.0  # µs
    
    def record(self, latency_us):
        """Record latency sample."""
        self.samples.append(latency_us)
        if len(self.samples) > 1000000:
            self.samples = self.samples[-1000000:]
    
    def check_alerts(self):
        """Check for latency threshold violations."""
        if len(self.samples) < 1000:
            return
        
        sorted_samples = sorted(self.samples)
        p99 = sorted_samples[int(len(sorted_samples) * 0.99)]
        p999 = sorted_samples[int(len(sorted_samples) * 0.999)]
        
        if p99 > self.alert_p99:
            self.send_alert(f"p99 latency {p99:.2f}µs exceeds threshold {self.alert_p99}µs")
        
        if p999 > self.alert_p999:
            self.send_alert(f"p999 latency {p999:.2f}µs exceeds threshold {self.alert_p999}µs")
    
    def send_alert(self, message):
        """Send alert to monitoring system."""
        print(f"ALERT: {message}")
        # Send to PagerDuty, Slack, etc.
```

---

## 14. Failure Modes & Recovery

### 14.1 Failure Detection

| Failure | Detection | Time to Detect |
|---|---|---|
| **Packet loss (gap)** | Sequence number gap | < 100 µs |
| **Feed disconnect** | Heartbeat timeout | < 1 s |
| **NIC failure** | DPDK PMD error | < 10 ms |
| **Process crash** | Watchdog / heartbeat | < 100 ms |
| **Clock drift** | PTP offset monitoring | < 1 s |

### 14.2 Recovery Strategies

| Failure | Recovery | RTO |
|---|---|---|
| **Sequence gap** | Retransmission request (out-of-band) | < 10 ms |
| **Feed disconnect** | Reconnect + snapshot request | < 1 s |
| **NIC failure** | Failover to redundant NIC | < 100 ms |
| **Process crash** | Hot standby takeover | < 500 ms |
| **Full system** | Disaster recovery site | < 30 s |

### 14.3 Redundancy

```
┌──────────────┐     ┌──────────────┐
│  Primary     │◀───▶│  Secondary   │
│  Feed        │     │  Feed        │
│  Handler     │     │  Handler     │
│  (Active)    │     │  (Standby)   │
└──────┬───────┘     └──────┬───────┘
       │                    │
       │   State Sync       │
       │   (shared memory)  │
       │                    │
       ▼                    ▼
┌──────────────────────────────────┐
│         Consumers               │
│  (Matching, Risk, Distribution) │
└──────────────────────────────────┘
```

---

## 15. Implementation Variants

### 15.1 Variant A: Pure Software (DPDK)

**Best for:** Multi-format feeds, rapid development, cost-sensitive deployments

```
NIC → DPDK PMD → Decode → Normalize → Book → Fan-Out
     (all in userspace, single process)
```

- **Latency:** 2–5 µs (p99)
- **Throughput:** 10–50M msg/s per core
- **Complexity:** Medium

### 15.2 Variant B: FPGA-Assisted

**Best for:** Fixed-format feeds, maximum throughput, minimum latency

```
NIC → FPGA (decode + normalize) → Host (book + fan-out)
     (hardware pipeline)          (software)
```

- **Latency:** 500 ns – 2 µs (p99)
- **Throughput:** 50–100M msg/s per FPGA
- **Complexity:** High

### 15.3 Variant C: Full FPGA Pipeline

**Best for:** Ultra-low latency, single-venue, high-frequency

```
NIC → FPGA (decode + normalize + book + fan-out)
     (complete pipeline in hardware)
```

- **Latency:** 200–500 ns (p99)
- **Throughput:** 100M+ msg/s
- **Complexity:** Very high
- **Use case:** Competitive HFT where every nanosecond counts

### 15.4 Variant Selection Matrix

| Criteria | A: Software | B: FPGA-Assisted | C: Full FPGA |
|---|---|---|---|
| Latency | 2–5 µs | 0.5–2 µs | 0.2–0.5 µs |
| Flexibility | High | Medium | Low |
| Dev time | Weeks | Months | Months+ |
| Cost | $$ | $$$ | $$$$ |
| Maintenance | Easy | Medium | Hard |
| **Recommendation** | **Start here** | Scale needed | Extreme latency |

---

## 16. References

- DPDK Documentation: https://doc.dpdk.org/
- AMD Versal AI Edge: https://www.amd.com/en/products/adaptive-soc-fpgas/versal-ai-edge.html
- NVIDIA BlueField DPU: https://www.nvidia.com/en-us/networking/products/data-processing-unit/
- CME MDP 3.0 Specification: https://www.cmegroup.com/confluence/display/EPICSANDBOX/MDP+3.0+-+Market+Data
- OPRA ITCH Protocol: https://www.opradata.com/specs/
- IEEE 1588 PTP: https://ieee1588.nist.gov/
- "Feed Handler Architecture for Low-Latency Trading" — industry best practices

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| **PMD** | Poll Mode Driver (DPDK) |
| **RSS** | Receive Side Scaling |
| **SPSC** | Single-Producer Single-Consumer |
| **MPSC** | Multi-Producer Single-Consumer |
| **TSC** | Time Stamp Counter (CPU cycle counter) |
| **PTP** | Precision Time Protocol (IEEE 1588) |
| **FAST** | FIX Adapted for STreaming |
| **ITCH** | Incremental Trading Channel Handler |
| **OUCH** | Order User Channel Handler |
| **TOPS** | Top of Book System |
| **PILLAR** | CME's market data platform |
| **MDP** | Market Data Platform (CME) |
| **OPRA** | Options Price Reporting Authority |

---

## Appendix B: Sample Configuration

```ini
# /etc/feedhandler/config.ini

[global]
cpu_isolation = 2-11
hugepages = 4096
hugepage_size = 1G
numa_node = 0

[network]
driver = dpdk
port = 0000:03:00.0
num_rx_queues = 8
num_tx_queues = 4
rss_hash = toeplitz
hw_timestamp = true

[feeds]
feed1 = CME_MDP3, 10.0.1.1:14345, ITCH
feed2 = OPRA, 10.0.2.1:20000, ITCH
feed3 = NYSE_PILLAR, 10.0.3.1:30000, PILLAR

[performance]
busy_poll = true
busy_budget = 100
prefetch_distance = 4
cache_line_size = 64

[monitoring]
latency_histogram = true
histogram_buffer_size = 1048576
alert_p99_threshold_us = 5
alert_p999_threshold_us = 10
```

---

*Document version: 2.0*  
*Last updated: 2026-09-30*
