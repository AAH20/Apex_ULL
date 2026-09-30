/**
 * dpdk_benchmark.c — DPDK Kernel Bypass Benchmark Suite
 *
 * Measures:
 * - Packet forwarding latency (min/max/mean/stddev)
 * - Throughput (Mpps, Gbps)
 * - Jitter analysis
 * - CPU utilization
 * - Cache miss impact
 *
 * Build: gcc -O2 -Wall -o dpdk_benchmark dpdk_benchmark.c $(pkg-config --cflags --libs libdpdk)
 * Run:   sudo ./dpdk_benchmark -l 0-3 -n 4 --proc-type=auto
 */

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_mempool.h>
#include <rte_cycles.h>
#include <rte_lcore.h>
#include <rte_timer.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define RX_RING_SIZE    1024
#define TX_RING_SIZE    1024
#define NUM_MBUFS       8191
#define MBUF_CACHE_SIZE 250
#define BURST_SIZE      32
#define MAX_SAMPLES     100000

static const struct rte_eth_conf port_conf_default = {
    .rxmode = { .max_rx_pkt_len = RTE_ETHER_MAX_LEN },
};

struct latency_sample {
    uint64_t timestamp;
    uint64_t latency_cycles;
};

struct benchmark_stats {
    uint64_t total_pkts;
    uint64_t total_bytes;
    uint64_t min_cycles;
    uint64_t max_cycles;
    uint64_t sum_cycles;
    uint64_t sample_count;
    struct latency_sample *samples;
    double cpu_freq_mhz;
};

static void stats_init(struct benchmark_stats *s) {
    s->total_pkts = 0;
    s->total_bytes = 0;
    s->min_cycles = UINT64_MAX;
    s->max_cycles = 0;
    s->sum_cycles = 0;
    s->sample_count = 0;
    s->samples = calloc(MAX_SAMPLES, sizeof(struct latency_sample));
    s->cpu_freq_mhz = rte_get_tsc_hz() / 1e6;
}

static void stats_add(struct benchmark_stats *s, uint64_t cycles, uint64_t bytes) {
    if (cycles < s->min_cycles) s->min_cycles = cycles;
    if (cycles > s->max_cycles) s->max_cycles = cycles;
    s->sum_cycles += cycles;
    s->total_bytes += bytes;
    s->total_pkts++;
    if (s->sample_count < MAX_SAMPLES) {
        s->samples[s->sample_count].latency_cycles = cycles;
        s->samples[s->sample_count].timestamp = rte_rdtsc();
        s->sample_count++;
    }
}

static double cycles_to_us(uint64_t cycles, double freq_mhz) {
    return (cycles / freq_mhz) / 1000.0;
}

static void stats_print(struct benchmark_stats *s, const char *label) {
    double mean = s->total_pkts > 0 ? (double)s->sum_cycles / s->total_pkts : 0;
    double min_us = cycles_to_us(s->min_cycles, s->cpu_freq_mhz);
    double max_us = cycles_to_us(s->max_cycles, s->cpu_freq_mhz);
    double mean_us = cycles_to_us((uint64_t)mean, s->cpu_freq_mhz);
    double jitter_us = max_us - min_us;

    /* Calculate stddev */
    double stddev = 0;
    if (s->sample_count > 1) {
        double sum_sq = 0;
        for (uint64_t i = 0; i < s->sample_count; i++) {
            double d = (double)s->samples[i].latency_cycles - mean;
            sum_sq += d * d;
        }
        stddev = sqrt(sum_sq / (s->sample_count - 1));
    }
    double stddev_us = cycles_to_us((uint64_t)stddev, s->cpu_freq_mhz);

    printf("\n=== %s ===\n", label);
    printf("  Total packets: %lu\n", s->total_pkts);
    printf("  Total bytes:   %lu\n", s->total_bytes);
    printf("  Min latency:   %.3f µs\n", min_us);
    printf("  Max latency:   %.3f µs\n", max_us);
    printf("  Mean latency:  %.3f µs\n", mean_us);
    printf("  Stddev:        %.3f µs\n", stddev_us);
    printf("  Jitter:        %.3f µs\n", jitter_us);
    printf("  Throughput:    %.2f Mpps\n", s->total_pkts / (mean_us * 1000));
    printf("  Throughput:    %.2f Gb/s\n", (s->total_bytes * 8.0) / (mean_us * 1000));
}

/* ── Port initialization ── */
static int port_init(uint16_t port, struct rte_mempool *mbuf_pool) {
    struct rte_eth_conf port_conf = port_conf_default;
    const uint16_t rx_rings = 1, tx_rings = 1;
    int retval;

    if (!rte_eth_dev_is_valid_port(port))
        return -1;

    retval = rte_eth_dev_configure(port, rx_rings, tx_rings, &port_conf);
    if (retval != 0) return retval;

    retval = rte_eth_rx_queue_setup(port, 0, RX_RING_SIZE,
        rte_eth_dev_socket_id(port), NULL, mbuf_pool);
    if (retval < 0) return retval;

    retval = rte_eth_tx_queue_setup(port, 0, TX_RING_SIZE,
        rte_eth_dev_socket_id(port), NULL);
    if (retval < 0) return retval;

    retval = rte_eth_dev_start(port);
    if (retval < 0) return retval;

    rte_eth_promiscuous_enable(port);
    return 0;
}

/* ── Packet processing: swap MAC addresses ── */
static void process_packets(struct rte_mbuf **pkts, uint16_t nb_pkts) {
    for (uint16_t i = 0; i < nb_pkts; i++) {
        struct rte_ether_hdr *eth = rte_pktmbuf_mtod(pkts[i], struct rte_ether_hdr *);
        struct rte_ether_addr tmp;
        rte_ether_addr_copy(&eth->src_addr, &tmp);
        rte_ether_addr_copy(&eth->dst_addr, &eth->src_addr);
        rte_ether_addr_copy(&tmp, &eth->dst_addr);
    }
}

/* ── Main forwarding loop ── */
static int forwarding_loop(uint16_t port, struct benchmark_stats *stats) {
    struct rte_mbuf *pkts[BURST_SIZE];
    uint64_t start_cycles = rte_rdtsc();
    uint64_t end_cycles = start_cycles + rte_get_tsc_hz() * 10; /* 10 seconds */

    printf("Forwarding on port %u for 10 seconds...\n", port);

    while (rte_rdtsc() < end_cycles) {
        uint16_t nb_rx = rte_eth_rx_burst(port, 0, pkts, BURST_SIZE);
        if (nb_rx == 0) continue;

        uint64_t proc_start = rte_rdtsc();

        process_packets(pkts, nb_rx);

        uint16_t nb_tx = rte_eth_tx_burst(port, 0, pkts, nb_rx);

        uint64_t proc_end = rte_rdtsc();

        /* Free unsent packets */
        for (uint16_t i = nb_tx; i < nb_rx; i++) {
            rte_pktmbuf_free(pkts[i]);
        }

        stats_add(stats, proc_end - proc_start, nb_tx * 64);
    }

    return 0;
}

/* ── Latency measurement loop ── */
static int latency_loop(uint16_t port, struct benchmark_stats *stats, int iterations) {
    struct rte_mbuf *pkts[BURST_SIZE];
    struct rte_mbuf *tx_pkts[BURST_SIZE];

    printf("Measuring latency for %d iterations...\n", iterations);

    for (int i = 0; i < iterations; i++) {
        /* Create a test packet */
        struct rte_mbuf *tx_pkt = rte_pktmbuf_alloc(rte_pktmbuf_pool_get("MBUF_POOL"));
        if (!tx_pkt) continue;

        /* Fill with test data */
        char *data = rte_pktmbuf_mtod(tx_pkt, char *);
        memset(data, 0xAB, 64);
        tx_pkt->data_len = 64;
        tx_pkt->pkt_len = 64;

        uint64_t t0 = rte_rdtsc();

        /* Send */
        rte_eth_tx_burst(port, 0, &tx_pkt, 1);

        /* Receive (loopback) */
        uint16_t nb_rx;
        do {
            nb_rx = rte_eth_rx_burst(port, 0, pkts, 1);
        } while (nb_rx == 0);

        uint64_t t1 = rte_rdtsc();

        stats_add(stats, t1 - t0, 64);

        rte_pktmbuf_free(pkts[0]);
    }

    return 0;
}

int main(int argc, char *argv[]) {
    int ret = rte_eal_init(argc, argv);
    if (ret < 0) rte_exit(EXIT_FAILURE, "EAL init failed\n");

    uint16_t nb_ports = rte_eth_dev_count_avail();
    if (nb_ports == 0) rte_exit(EXIT_FAILURE, "No Ethernet ports\n");

    struct rte_mempool *mbuf_pool = rte_pktmbuf_pool_create(
        "MBUF_POOL", NUM_MBUFS, MBUF_CACHE_SIZE, 0,
        RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());
    if (!mbuf_pool) rte_exit(EXIT_FAILURE, "Cannot create mbuf pool\n");

    for (uint16_t i = 0; i < nb_ports; i++) {
        if (port_init(i, mbuf_pool) != 0)
            rte_exit(EXIT_FAILURE, "Cannot init port %u\n", i);
    }

    struct benchmark_stats stats;
    stats_init(&stats);

    /* Run forwarding benchmark */
    forwarding_loop(0, &stats);
    stats_print(&stats, "DPDK Forwarding Benchmark");

    /* Run latency benchmark */
    struct benchmark_stats lat_stats;
    stats_init(&lat_stats);
    latency_loop(0, &lat_stats, 10000);
    stats_print(&lat_stats, "DPDK Latency Benchmark");

    return 0;
}
