# Ultra-Low Latency Tutorials

**Version:** 1.0  
**Last Updated:** 2026-09-29

---

## Available Tutorials

| # | Tutorial | Domain | Difficulty | Duration |
|---|----------|--------|------------|----------|
| 1 | [DPDK Packet Processing](tutorials/dpdk-packet-processing.md) | Network | Intermediate | 2–3 hours |
| 2 | [RDMA Echo Server](tutorials/rdma-echo-server.md) | Network | Advanced | 3–4 hours |
| 3 | [FPGA Feed Handler](tutorials/fpga-feed-handler.md) | HFT | Advanced | 4–6 hours |
| 4 | [Kernel Tuning for ULL](tutorials/kernel-tuning.md) | System | Beginner | 1–2 hours |
| 5 | [Latency Measurement](tutorials/latency-measurement.md) | System | Beginner | 1 hour |
| 6 | [P4 Switch Pipeline](tutorials/p4-switch-pipeline.md) | Network | Advanced | 3–4 hours |

---

## Prerequisites

### Hardware

- **DPDK/RDMA:** Intel or AMD NIC with DPDK support (Intel X710, Mellanox ConnectX-5/6/7)
- **FPGA:** Xilinx/AMD or Intel FPGA dev board (optional for FPGA tutorials)
- **General:** Multi-core x86_64 CPU, 16+ GB RAM, Linux kernel 5.10+

### Software

```bash
# Ubuntu/Debian
sudo apt install build-essential cmake git
sudo apt install dpdk dpdk-dev libibverbs-dev librdmacm-dev
sudo apt install libspdk-dev spdk
sudo apt install python3-pip

# Python dependencies
pip3 install p4runtime psutil numpy matplotlib
```

---

## Tutorial Structure

Each tutorial follows this format:

1. **Overview** — What you'll build and why
2. **Prerequisites** — Hardware and software requirements
3. **Step-by-step** — Detailed instructions with code
4. **Verification** — How to confirm it works
5. **Troubleshooting** — Common issues and fixes
6. **Next Steps** — Where to go from here

---

## Quick Start: Kernel Tuning

If you're new to ULL, start with [Kernel Tuning for ULL](tutorials/kernel-tuning.md) — it requires no special hardware and teaches the foundational concepts.

---

## Learning Path

### Beginner
1. [Kernel Tuning for ULL](tutorials/kernel-tuning.md)
2. [Latency Measurement](tutorials/latency-measurement.md)

### Intermediate
3. [DPDK Packet Processing](tutorials/dpdk-packet-processing.md)
4. [RDMA Echo Server](tutorials/rdma-echo-server.md)

### Advanced
5. [FPGA Feed Handler](tutorials/fpga-feed-handler.md)
6. [P4 Switch Pipeline](tutorials/p4-switch-pipeline.md)

---

## Contributing

To add a new tutorial:

1. Create a new file in `docs/tutorials/`
2. Follow the tutorial structure above
3. Add an entry to the table at the top of this file
4. Update the learning path if appropriate
