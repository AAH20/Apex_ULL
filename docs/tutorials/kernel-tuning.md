# Tutorial: Kernel Tuning for Ultra-Low Latency

**Domain:** System  
**Difficulty:** Beginner  
**Duration:** 1–2 hours

---

## Overview

In this tutorial, you'll learn how to configure a Linux system for ultra-low-latency workloads. These techniques apply to any ULL application — DPDK, RDMA, FPGA, or custom kernel bypass.

## What You'll Configure

1. CPU isolation and frequency scaling
2. Hugepages for large memory allocations
3. Network stack tuning
4. IRQ affinity
5. Kernel boot parameters

## Prerequisites

- Linux kernel 5.10+ (Ubuntu 22.04 or similar)
- Root/sudo access
- `sysctl` and `grub` tools

---

## Step 1: CPU Isolation

Isolate specific cores from the general scheduler so your ULL application has dedicated CPU resources.

```bash
# Edit kernel boot parameters
sudo nano /etc/default/grub

# Add to GRUB_CMDLINE_LINUX:
# isolcpus=2-7 nohz_full=2-7 rcu_nocbs=2-7 intel_pstate=disable

sudo update-grub
sudo reboot
```

**What this does:**
- `isolcpus=2-7` — Cores 2-7 are excluded from the scheduler
- `nohz_full=2-7` — No timer ticks on these cores
- `rcu_nocbs=2-7` — RCU callbacks offloaded to other cores
- `intel_pstate=disable` — Disable CPU frequency scaling

## Step 2: Hugepages

Large pages reduce TLB misses and improve memory access latency.

```bash
# Allocate 8 x 1GB hugepages
echo 8 | sudo tee /proc/sys/vm/nr_hugepages

# Or persistently:
echo "vm.nr_hugepages = 8" | sudo tee -a /etc/sysctl.conf

# Mount hugepages
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs nodev /mnt/huge

# Verify
cat /proc/meminfo | grep Huge
```

## Step 3: Network Stack Tuning

```bash
# /etc/sysctl.conf
sudo tee -a /etc/sysctl.conf << 'EOF'

# Network buffers
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.netdev_max_backlog = 300000
net.core.somaxconn = 65535

# TCP tuning
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_notsent_lowat = 16384

# Disable NUMA balancing
kernel.numa_balancing = 0

# Disable watchdog
kernel.watchdog = 0

# Real-time scheduling
kernel.sched_rt_runtime_us = -1
EOF

sudo sysctl -p
```

## Step 4: IRQ Affinity

Pin network interrupts to specific cores to avoid interference with your application.

```bash
# Find your NIC's IRQ
grep eth0 /proc/interrupts
# Example output: 42:  12345  0  PCI-MSI-edge  eth0-rx-0

# Pin IRQ 42 to core 2
echo 4 | sudo tee /proc/irq/42/smp_affinity

# Or use irqbalance with manual hints
sudo systemctl stop irqbalance
echo 4 | sudo tee /proc/irq/42/smp_affinity
```

## Step 5: CPU Frequency and Idle States

```bash
# Disable CPU frequency scaling
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Disable C-states (prevent CPU from sleeping)
# Add to kernel boot parameters: processor.max_cstate=1 idle=poll

# Verify
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# Should show: performance
```

## Step 6: NUMA Optimization

```bash
# Check NUMA topology
numactl --hardware

# Run application on specific NUMA node
numactl --cpunodebind=0 --membind=0 ./my_ull_app

# Or in code:
#include <numa.h>
numa_run_on_node(0);
numa_set_preferred(0);
```

## Step 7: Verification Script

```bash
#!/bin/bash
# verify_ull_tuning.sh

echo "=== CPU Isolation ==="
cat /sys/devices/system/cpu/isolated

echo "=== Hugepages ==="
grep Huge /proc/meminfo

echo "=== CPU Frequency ==="
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

echo "=== IRQ Affinity ==="
for irq in $(grep eth0 /proc/interrupts | awk -F: '{print $1}'); do
    echo "IRQ $irq: $(cat /proc/irq/$irq/smp_affinity)"
done

echo "=== Network Buffers ==="
sysctl net.core.rmem_max net.core.wmem_max

echo "=== NUMA ==="
numactl --show
```

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Context switches/sec | 10,000+ | <100 |
| Timer interrupts/sec | 1,000 | 0 (isolated cores) |
| TLB misses | High | Reduced 10–100x |
| Latency jitter | High | Minimal |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot allocate hugepages" | Increase `vm.nr_hugepages`, reboot |
| "IRQ affinity write failed" | Check IRQ number, verify IRQ exists |
| "CPU frequency not changing" | Disable `intel_pstate` in kernel params |
| "Application slow on NUMA" | Use `numactl` to bind to correct node |

## Next Steps

- Move to [Latency Measurement](latency-measurement.md) to verify your tuning
- Proceed to [DPDK Packet Processing](dpdk-packet-processing.md) for kernel bypass
- Explore [RDMA Echo Server](rdma-echo-server.md) for RDMA configuration
