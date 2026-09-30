# Tutorial: DPDK Packet Processing

**Domain:** Network  
**Difficulty:** Intermediate  
**Duration:** 2–3 hours

---

## Overview

In this tutorial, you'll build a minimal DPDK application that receives packets, processes them in user space (bypassing the kernel), and transmits them back. This is the foundation of all kernel-bypass networking.

## What You'll Build

A DPDK-based packet forwarder that:
1. Initializes DPDK with hugepages
2. Configures a NIC port in poll mode
3. Receives packets, modifies them, and transmits them
4. Measures throughput and latency

## Prerequisites

- Intel X710 or Mellanox ConnectX-5+ NIC
- Linux kernel 5.10+
- DPDK 23.11+ installed
- 1 GB hugepages configured

---

## Step 1: Environment Setup

```bash
# Verify DPDK installation
dpdk-devbind.py --status

# Bind NIC to DPDK-compatible driver
sudo dpdk-devbind.py --bind=vfio-pci 0000:03:00.0

# Verify hugepages
cat /proc/meminfo | grep Huge
# Should show: Hugepages_Total: 8
```

## Step 2: Create the Application

```c
// dpdk_forwarder.c
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_mempool.h>
#include <stdio.h>
#include <stdint.h>

#define RX_RING_SIZE 1024
#define TX_RING_SIZE 1024
#define NUM_MBUFS 8191
#define MBUF_CACHE_SIZE 250
#define BURST_SIZE 32

static const struct rte_eth_conf port_conf_default = {
    .rxmode = { .max_rx_pkt_len = RTE_ETHER_MAX_LEN },
};

int main(int argc, char *argv[]) {
    // Initialize EAL
    int ret = rte_eal_init(argc, argv);
    if (ret < 0) rte_exit(EXIT_FAILURE, "EAL init failed\n");

    uint16_t port_id = 0;
    uint16_t nb_ports = rte_eth_dev_count_avail();
    if (nb_ports == 0) rte_exit(EXIT_FAILURE, "No Ethernet ports\n");

    // Create memory pool
    struct rte_mempool *mbuf_pool = rte_pktmbuf_pool_create(
        "MBUF_POOL", NUM_MBUFS, MBUF_CACHE_SIZE, 0,
        RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());
    if (!mbuf_pool) rte_exit(EXIT_FAILURE, "Cannot create mbuf pool\n");

    // Configure port
    struct rte_eth_conf port_conf = port_conf_default;
    ret = rte_eth_dev_configure(port_id, 1, 1, &port_conf);
    if (ret < 0) rte_exit(EXIT_FAILURE, "Cannot configure port\n");

    // Setup RX queue
    ret = rte_eth_rx_queue_setup(port_id, 0, RX_RING_SIZE,
        rte_eth_dev_socket_id(port_id), NULL, mbuf_pool);
    if (ret < 0) rte_exit(EXIT_FAILURE, "Cannot setup RX queue\n");

    // Setup TX queue
    ret = rte_eth_tx_queue_setup(port_id, 0, TX_RING_SIZE,
        rte_eth_dev_socket_id(port_id), NULL);
    if (ret < 0) rte_exit(EXIT_FAILURE, "Cannot setup TX queue\n");

    // Start device
    ret = rte_eth_dev_start(port_id);
    if (ret < 0) rte_exit(EXIT_FAILURE, "Cannot start port\n");

    // Enable promiscuous mode
    rte_eth_promiscuous_enable(port_id);

    printf("DPDK forwarder running on port %u\n", port_id);

    // Main loop
    struct rte_mbuf *pkts[BURST_SIZE];
    uint64_t total_pkts = 0;
    uint64_t total_bytes = 0;

    while (1) {
        // Receive burst
        uint16_t nb_rx = rte_eth_rx_burst(port_id, 0, pkts, BURST_SIZE);
        if (nb_rx == 0) continue;

        // Process packets (example: swap MAC addresses)
        for (int i = 0; i < nb_rx; i++) {
            struct rte_ether_hdr *eth = rte_pktmbuf_mtod(pkts[i],
                struct rte_ether_hdr *);
            struct rte_ether_addr tmp;
            rte_ether_addr_copy(&eth->src_addr, &tmp);
            rte_ether_addr_copy(&eth->dst_addr, &eth->src_addr);
            rte_ether_addr_copy(&tmp, &eth->dst_addr);
        }

        // Transmit burst
        uint16_t nb_tx = rte_eth_tx_burst(port_id, 0, pkts, nb_rx);
        
        // Free unsent packets
        for (int i = nb_tx; i < nb_rx; i++) {
            rte_pktmbuf_free(pkts[i]);
        }

        total_pkts += nb_tx;
        total_bytes += nb_tx * 64;  // Approximate
    }

    return 0;
}
```

## Step 3: Build

```makefile
# Makefile
APP = dpdk_forwarder

# DPDK paths
DPDK_PATH ?= /usr/local/dpdk
CFLAGS += -O3 -g -I$(DPDK_PATH)/include
LDFLAGS += -L$(DPDK_PATH)/lib -lrte_eal -lrte_ethdev -lrte_mbuf \
           -lrte_mempool -lrte_ring -lrte_kvargs -lrte_net \
           -lrte_ether -lrte_cmdline -lrte_pci -lrte_bus_pci \
           -lrte_bus_vdev -lrte_timer -lrte_hash -lrte_lpm \
           -lrte_acl -lrte_meter -lrte_sched -lrte_port \
           -lrte_table -lrte_pipeline -lrte_flow -lrte_security \
           -lrte_ipsec -lrte_gso -lrte_gro -lrte_hash_crc \
           -lrte_hash_jhash -lrte_hash_xmm -lrte_rcu \
           -lrte_stack -lrte_node -lrte_rib -lrte_fib \
           -lrte_lpm6 -lrte_rib6 -lrte_fib6 -lrte_arp \
           -lrte_mld -lrte_icmp -lrte_igmp -lrte_ip \
           -lrte_ip6 -lrte_tcp -lrte_udp -lrte_sctp \
           -lrte_esp -lrte_ah -lrte_crypto -lrte_cryptodev \
           -lrte_compressdev -lrte_bbdev -lrte_bitratestats \
           -lrte_latencystats -lrte_pcap -lrte_distributor \
           -lrte_reorder -lrte_efd -lrte_member -lrte_eventdev \
           -lrte_rawdev -lrte_regexdev -lrte_vdpa -lrte_cfgfile \
           -lrte_gso -lrte_gro -lrte_ipfrag -lrte_ipsec \
           -lrte_sched -lrte_meter -lrte_port -lrte_table \
           -lrte_pipeline -lrte_flow -lrte_security -lrte_stack \
           -lrte_node -lrte_rib -lrte_fib -lrte_lpm6 -lrte_rib6 \
           -lrte_fib6 -lrte_arp -lrte_mld -lrte_icmp -lrte_igmp \
           -lrte_ip -lrte_ip6 -lrte_tcp -lrte_udp -lrte_sctp \
           -lrte_esp -lrte_ah -lrte_crypto -lrte_cryptodev \
           -lrte_compressdev -lrte_bbdev -lrte_bitratestats \
           -lrte_latencystats -lrte_pcap -lrte_distributor \
           -lrte_reorder -lrte_efd -lrte_member -lrte_eventdev \
           -lrte_rawdev -lrte_regexdev -lrte_vdpa -lrte_cfgfile \
           -Wl,--whole-archive -lrte_bus_vdev -lrte_bus_pci \
           -lrte_pci -lrte_ethdev -lrte_mbuf -lrte_mempool \
           -lrte_ring -lrte_kvargs -lrte_eal -lrte_net \
           -lrte_ether -lrte_cmdline -lrte_timer -lrte_hash \
           -lrte_lpm -lrte_acl -lrte_meter -lrte_sched \
           -lrte_port -lrte_table -lrte_pipeline -lrte_flow \
           -lrte_security -lrte_ipsec -lrte_gso -lrte_gro \
           -lrte_hash_crc -lrte_hash_jhash -lrte_hash_xmm \
           -lrte_rcu -lrte_stack -lrte_node -lrte_rib \
           -lrte_fib -lrte_lpm6 -lrte_rib6 -lrte_fib6 \
           -lrte_arp -lrte_mld -lrte_icmp -lrte_igmp \
           -lrte_ip -lrte_ip6 -lrte_tcp -lrte_udp -lrte_sctp \
           -lrte_esp -lrte_ah -lrte_crypto -lrte_cryptodev \
           -lrte_compressdev -lrte_bbdev -lrte_bitratestats \
           -lrte_latencystats -lrte_pcap -lrte_distributor \
           -lrte_reorder -lrte_efd -lrte_member -lrte_eventdev \
           -lrte_rawdev -lrte_regexdev -lrte_vdpa -lrte_cfgfile \
           -Wl,--no-whole-archive -lpthread -lm -ldl -lnuma

all: $(APP)

$(APP): dpdk_forwarder.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(APP)
```

## Step 4: Run

```bash
# Run with 2 cores, 1GB memory
sudo ./dpdk_forwarder -l 0-1 -n 1 --proc-type=auto
```

## Step 5: Verify

```bash
# In another terminal, generate traffic
sudo ping -I eth0 10.0.0.1

# Check DPDK port statistics
# (Add rte_eth_stats_get() to your code for detailed stats)
```

## Expected Results

| Metric | Value |
|--------|-------|
| Throughput | 10–40 Mpps (64B packets) |
| Latency | 1–10 µs |
| CPU usage | 100% per core (polling) |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No Ethernet ports" | Check `dpdk-devbind.py --status` |
| "Cannot create mbuf pool" | Increase hugepages: `echo 8 > /proc/sys/vm/nr_hugepages` |
| "EAL init failed" | Check core list with `lscpu` |
| Low throughput | Increase burst size, check NUMA alignment |

## Next Steps

- Add multiple RX/TX queues for parallelism
- Implement flow classification (5-tuple)
- Add hardware timestamping for latency measurement
- Move to [RDMA Echo Server](rdma-echo-server.md) for cross-host communication
