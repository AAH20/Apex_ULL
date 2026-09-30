# Makefile for DPDK Implementation
# Build: make all
# Test:  make test
# Clean: make clean

CC = gcc
CFLAGS = -O2 -Wall -Wextra $(shell pkg-config --cflags libdpdk 2>/dev/null || echo "-I/usr/local/dpdk/include")
LDFLAGS = $(shell pkg-config --libs libdpdk 2>/dev/null || echo "-L/usr/local/dpdk/lib -lrte_eal -lrte_ethdev -lrte_mbuf -lrte_mempool -lrte_ring -lrte_kvargs -lrte_net -lrte_ether -lrte_cmdline -lrte_pci -lrte_bus_pci -lrte_bus_vdev -lrte_timer -lrte_hash -lrte_lpm -lrte_acl -lrte_meter -lrte_sched -lrte_port -lrte_table -lrte_pipeline -lrte_flow -lrte_security -lrte_ipsec -lrte_gso -lrte_gro -lrte_hash_crc -lrte_hash_jhash -lrte_hash_xmm -lrte_rcu -lrte_stack -lrte_node -lrte_rib -lrte_fib -lrte_lpm6 -lrte_rib6 -lrte_fib6 -lrte_arp -lrte_mld -lrte_icmp -lrte_igmp -lrte_ip -lrte_ip6 -lrte_tcp -lrte_udp -lrte_sctp -lrte_esp -lrte_ah -lrte_crypto -lrte_cryptodev -lrte_compressdev -lrte_bbdev -lrte_bitratestats -lrte_latencystats -lrte_pcap -lrte_distributor -lrte_reorder -lrte_efd -lrte_member -lrte_eventdev -lrte_rawdev -lrte_regexdev -lrte_vdpa -lrte_cfgfile -Wl,--whole-archive -lrte_bus_vdev -lrte_bus_pci -lrte_pci -lrte_ethdev -lrte_mbuf -lrte_mempool -lrte_ring -lrte_kvargs -lrte_eal -lrte_net -lrte_ether -lrte_cmdline -lrte_timer -lrte_hash -lrte_lpm -lrte_acl -lrte_meter -lrte_sched -lrte_port -lrte_table -lrte_pipeline -lrte_flow -lrte_security -lrte_ipsec -lrte_gso -lrte_gro -lrte_hash_crc -lrte_hash_jhash -lrte_hash_xmm -lrte_rcu -lrte_stack -lrte_node -lrte_rib -lrte_fib -lrte_lpm6 -lrte_rib6 -lrte_fib6 -lrte_arp -lrte_mld -lrte_icmp -lrte_igmp -lrte_ip -lrte_ip6 -lrte_tcp -lrte_udp -lrte_sctp -lrte_esp -lrte_ah -lrte_crypto -lrte_cryptodev -lrte_compressdev -lrte_bbdev -lrte_bitratestats -lrte_latencystats -lrte_pcap -lrte_distributor -lrte_reorder -lrte_efd -lrte_member -lrte_eventdev -lrte_rawdev -lrte_regexdev -lrte_vdpa -lrte_cfgfile -Wl,--no-whole-archive -lpthread -lm -ldl -lnuma")

TARGETS = dpdk_benchmark

.PHONY: all test clean

all: $(TARGETS)

dpdk_benchmark: dpdk_benchmark.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

test: all
	sudo python3 test_dpdk.py

clean:
	rm -f $(TARGETS) *.o
