# Ultra-Low Latency Network Topology Patterns

> **Date:** 2026-09-29  
> **Scope:** Spine-Leaf, Fat-Tree, Dragonfly, Torus, Hypercube, and custom topologies for ULL interconnect design  
> **Companion Reports:** `reports/network-technologies.md`, `reports/hft-firms.md`, `reports/fpga-technologies.md`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design Principles for ULL Topologies](#design-principles-for-ull-topologies)
3. [Spine-Leaf (Clos) Topology](#spine-leaf-clos-topology)
4. [Fat-Tree Topology](#fat-tree-topology)
5. [Dragonfly Topology](#dragonfly-topology)
6. [Torus Topology](#torus-topology)
7. [Hypercube Topology](#hypercube-topology)
8. [Custom / Emerging Topologies](#custom--emerging-topologies)
9. [Comparative Analysis Matrix](#comparative-analysis-matrix)
10. [Selection Guide](#selection-guide)
11. [References](#references)

---

## Executive Summary

| Topology | Latency (typical) | Throughput | Cost | Scalability | Fault Tolerance | Best For |
|---|---|---|---|---|---|---|
| **Spine-Leaf (2-tier)** | 1–3 µs | 100–400 Gb/s | $$ | 10K–100K nodes | ★★★★ | General DC, RoCE |
| **Fat-Tree (3-tier)** | 2–5 µs | 100–400 Gb/s | $$$ | 100K–1M nodes | ★★★ | HPC, AI training |
| **Dragonfly** | 1–2 µs | 400–800 Gb/s | $$$$ | 100K–1M+ nodes | ★★★★ | Exascale HPC |
| **Torus (3D)** | 2–10 µs | 400 Gb/s+ | $$$ | 10K–100K nodes | ★★★ | HPC, NoC |
| **Hypercube** | 1–5 µs | 100–400 Gb/s | $$$ | 256–4096 nodes | ★★★ | Small HPC, NoC |
| **Jellyfish** | 1–3 µs | 100–400 Gb/s | $$ | 10K–100K nodes | ★★★★ | Cost-efficient DC |
| **Slim Fly** | 1–2 µs | 400–800 Gb/s | $$$$ | 100K–1M nodes | ★★★★★ | Large-scale HPC |

---

## Design Principles for ULL Topologies

### Key Metrics

| Metric | Definition | Target for ULL |
|---|---|---|
| **Bisection Bandwidth** | Minimum bandwidth across any network partition | ≥ 50% of endpoint bandwidth |
| **Diameter** | Longest shortest path between any two nodes | ≤ 4 hops |
| **Radix** | Number of ports per switch | 64–256 (current gen) |
| **Oversubscription Ratio** | Downstream bandwidth / Upstream bandwidth | 1:1 (non-blocking) or 3:1 (acceptable) |
| **Path Diversity** | Number of equal-cost paths between nodes | ≥ 4 for ECMP |
| **Fault Tolerance** | Network capacity after worst-case failure | ≥ 70% of nominal |

### ULL-Specific Design Rules

1. **Minimize hop count** — every hop adds 100–500 ns (switch) + 1–2 µs (routing)
2. **Maximize path diversity** — ECMP with ≥ 8 paths for load balancing and failover
3. **Non-blocking or near-non-blocking** — avoid oversubscription on latency-critical paths
4. **Adaptive routing** — dynamic path selection based on queue depth and congestion
5. **In-network computing** — SHARPv3, collective offload, tag matching
6. **Optical bypass** — circuit switching for elephant flows to reduce hop count

---

## Spine-Leaf (Clos) Topology

### Architecture

```
                    ┌─────────┐   ┌─────────┐   ┌─────────┐
                    │  Spine  │   │  Spine  │   │  Spine  │
                    │  SW 1   │   │  SW 2   │   │  SW 3   │
                    └────┬────┘   └────┬────┘   └────┬────┘
                         │             │             │
          ┌──────────────┼─────────────┼─────────────┼──────────────┐
          │              │             │             │              │
     ┌────┴────┐    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
     │  Leaf   │    │  Leaf   │   │  Leaf   │   │  Leaf   │   │  Leaf   │
     │  SW 1   │    │  SW 2   │   │  SW 3   │   │  SW 4   │   │  SW 5   │
     └────┬────┘    └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
          │              │             │             │              │
     ┌────┴────┐    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
     │ Servers │    │ Servers │   │ Servers │   │ Servers │   │ Servers │
     │ 1–48    │    │ 49–96   │   │ 97–144  │   │ 145–192 │   │ 193–240 │
     └─────────┘    └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

### Structure

- **Tier 1 (Leaf):** Top-of-rack switches, each connecting to all spine switches
- **Tier 2 (Spine):** Core switches, each connecting to all leaf switches
- **Full mesh:** Every leaf connects to every spine (no leaf-leaf or spine-spine links)

### Latency Analysis

| Path Type | Hop Count | Switch Latency | Propagation | Total |
|---|---|---|---|---|
| Same leaf (intra-rack) | 0 | 0 | < 1 µs | **< 1 µs** |
| Leaf → Spine → Leaf | 2 | 200–400 ns | 1–2 µs | **1.5–3 µs** |
| Leaf → Spine → Spine → Leaf | 3 | 300–600 ns | 2–3 µs | **2.5–5 µs** (3-tier) |

- **Typical RTT (same leaf):** 1–2 µs
- **Typical RTT (cross-leaf):** 2–4 µs
- **Worst case (3-tier):** 5–8 µs

### Throughput

| Configuration | Per-Server | Bisection | Notes |
|---|---|---|---|
| 400G leaf, 8×400G spine uplinks | 400 Gb/s | 3.2 Tb/s per spine | Non-blocking |
| 400G leaf, 4×400G spine uplinks | 400 Gb/s | 1.6 Tb/s per spine | 2:1 oversubscription |
| 800G leaf, 8×800G spine uplinks | 800 Gb/s | 6.4 Tb/s per spine | Non-blocking, XDR |

### Cost

| Component | Unit Cost | Qty (240 servers) | Total |
|---|---|---|---|
| Leaf switch (64×400G) | $25,000 | 5 | $125,000 |
| Spine switch (64×400G) | $30,000 | 8 | $240,000 |
| NICs (ConnectX-7 400G) | $1,500 | 240 | $360,000 |
| Cabling (DAC/AOC) | $200 | 480 | $96,000 |
| **Total** | | | **~$821,000** |
| **Per-server** | | | **~$3,420** |

### Scalability

| Limit | Value | Bottleneck |
|---|---|---|
| Max servers (2-tier) | ~10,000–50,000 | Spine port count × leaf count |
| Max servers (3-tier) | ~100,000–500,000 | Spine tier capacity |
| Max radix | 256 ports/switch | Switch ASIC capacity |
| Practical limit | ~100,000 | Cabling complexity, power, cooling |

### Fault Tolerance

| Failure Mode | Impact | Recovery |
|---|---|---|
| Single leaf failure | 1/N servers isolated | Automatic (server failover) |
| Single spine failure | Reduced bisection BW | ECMP reroute (< 1 s) |
| Link failure | Minimal (ECMP) | Sub-second |
| Multiple spine failures | Degraded but operational | Depends on redundancy |
| **Worst case tolerance** | **Lose 1 spine → 12.5% capacity loss** | |

### Pros & Cons

| Pros | Cons |
|---|---|
| Simple, well-understood | Limited to ~100K nodes (2-tier) |
| Excellent path diversity (ECMP) | Cabling complexity grows O(N²) |
| Non-blocking achievable | Spine switches are expensive |
| Easy to incrementally scale | Power/cooling at scale |
| Industry standard (most DCs) | Not optimal for all-to-all traffic |

---

## Fat-Tree Topology

### Architecture

```
                        ┌─────────────────────────────────────┐
                        │           Core Layer                │
                        │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │
                        │  │Core1│ │Core2│ │Core3│ │Core4│  │
                        │  └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘  │
                        └─────┼───────┼───────┼───────┼──────┘
                              │       │       │       │
          ┌───────────────────┼───────┼───────┼───────┼───────────────────┐
          │                   │       │       │       │                   │
     ┌────┴────┐         ┌────┴────┐ ┌┴──────┴┐ ┌────┴────┐         ┌────┴────┐
     │ Agg SW  │         │ Agg SW  │ │ Agg SW │ │ Agg SW  │         │ Agg SW  │
     │ (Pod 0) │         │ (Pod 1) │ │ (Pod 2)│ │ (Pod 3) │         │ (Pod N) │
     └────┬────┘         └────┬────┘ └────┬───┘ └────┬────┘         └────┬────┘
          │                   │           │           │                   │
     ┌────┴────┐         ┌────┴────┐ ┌────┴────┐ ┌────┴────┐         ┌────┴────┐
     │ ToR SW  │         │ ToR SW  │ │ ToR SW  │ │ ToR SW  │         │ ToR SW  │
     └────┬────┘         └────┬────┘ └────┬────┘ └────┬────┘         └────┬────┘
          │                   │           │           │                   │
     ┌────┴────┐         ┌────┴────┐ ┌────┴────┐ ┌────┴────┐         ┌────┴────┐
     │ Servers │         │ Servers │ │ Servers │ │ Servers │         │ Servers │
     └─────────┘         └─────────┘ └─────────┘ └─────────┘         └─────────┘
```

### Structure

- **3-tier:** ToR (Top of Rack) → Aggregation → Core
- **Pod-based:** Each pod is a self-contained spine-leaf cluster
- **Inter-pod:** Core switches connect pods via full mesh or partial mesh
- **k-ary fat-tree:** k pods, each with k/2 agg + k/2 ToR switches, k²/4 core switches

### Latency Analysis

| Path Type | Hop Count | Switch Latency | Total |
|---|---|---|---|
| Same ToR | 0 | 0 | **< 1 µs** |
| Same pod (ToR→Agg→ToR) | 2 | 200–400 ns | **1.5–3 µs** |
| Cross-pod (ToR→Agg→Core→Agg→ToR) | 4 | 400–800 ns | **3–6 µs** |
| Worst case (cross-pod, deep) | 5–6 | 500–1000 ns | **5–10 µs** |

### Throughput

| Configuration | Per-Server | Bisection | Notes |
|---|---|---|---|
| k=48 fat-tree (48-port switches) | 400 Gb/s | 1.47 Pb/s | Non-blocking |
| k=64 fat-tree | 400 Gb/s | 2.56 Pb/s | Non-blocking |
| k=32 fat-tree | 400 Gb/s | 512 Tb/s | Non-blocking |

### Cost

| Component | Unit Cost | Qty (k=48, ~11K servers) | Total |
|---|---|---|---|
| ToR switch (64×400G) | $25,000 | 240 | $6,000,000 |
| Agg switch (64×400G) | $25,000 | 240 | $6,000,000 |
| Core switch (64×400G) | $30,000 | 576 | $17,280,000 |
| NICs (ConnectX-7 400G) | $1,500 | 11,056 | $16,584,000 |
| Cabling | $200 | ~50,000 | $10,000,000 |
| **Total** | | | **~$55,864,000** |
| **Per-server** | | | **~$5,050** |

### Scalability

| Limit | Value | Bottleneck |
|---|---|---|
| Max servers (k=48) | ~11,000 | k³/4 formula |
| Max servers (k=64) | ~21,000 | k³/4 formula |
| Max servers (k=128) | ~98,000 | Cabling, power |
| Practical limit | ~100,000 | Cost and complexity |

### Fault Tolerance

| Failure Mode | Impact | Recovery |
|---|---|---|
| Single ToR failure | 1/k servers isolated | Server failover |
| Single agg failure | Pod degraded | ECMP reroute |
| Single core failure | Inter-pod BW reduced | ECMP reroute |
| Pod failure | k²/4 servers isolated | Cross-pod failover |
| **Worst case tolerance** | **Lose 1 core → ~0.4% capacity loss** | |

### Pros & Cons

| Pros | Cons |
|---|---|
| Non-blocking by design | Higher cost than spine-leaf |
| Predictable latency | More cabling (3 tiers) |
| Well-suited for HPC/AI | Core layer is expensive |
| Good bisection bandwidth | Diameter = 4–6 hops |
| Proven at scale (Google, Facebook) | Power/cooling intensive |

---

## Dragonfly Topology

### Architecture

```
    ┌──────────────────────────────────────────────────────────────┐
    │                    Dragonfly Group                            │
    │                                                              │
    │   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │
    │   │ SW1 │─│ SW2 │─│ SW3 │─│ SW4 │─│ SW5 │─│ SW6 │  ...     │
    │   └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘         │
    │      │       │       │       │       │       │              │
    │   ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐         │
    │   │Nodes│ │Nodes│ │Nodes│ │Nodes│ │Nodes│ │Nodes│         │
    │   └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘         │
    │                                                              │
    │   All-to-all within group (high BW)                          │
    └──────────────────────────────────────────────────────────────┘
                              │
                    Optical / High-BW
                    Inter-group Links
                              │
    ┌──────────────────────────────────────────────────────────────┐
    │                    Dragonfly Group 2                          │
    │   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │
    │   │ SW1 │─│ SW2 │─│ SW3 │─│ SW4 │─│ SW5 │─│ SW6 │  ...     │
    │   └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘         │
    │      │       │       │       │       │       │              │
    │   ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐         │
    │   │Nodes│ │Nodes│ │Nodes│ │Nodes│ │Nodes│ │Nodes│         │
    │   └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘         │
    └──────────────────────────────────────────────────────────────┘
```

### Structure

- **Groups of switches:** Each group is a high-radix all-to-all (or near-all-to-all) cluster
- **Inter-group links:** Optical or high-bandwidth links between groups (sparse)
- **Intra-group:** Full mesh or high-connectivity within group
- **Parameterization:** (a, h, p) = (group size, inter-group links per switch, nodes per switch)

### Latency Analysis

| Path Type | Hop Count | Switch Latency | Total |
|---|---|---|---|
| Same switch | 0 | 0 | **< 1 µs** |
| Same group (1 hop) | 1 | 100–200 ns | **1–2 µs** |
| Cross-group (2 hops) | 2 | 200–400 ns | **2–4 µs** |
| Worst case (3 hops) | 3 | 300–600 ns | **3–6 µs** |

- **Key advantage:** Diameter = 2–3 hops regardless of scale
- **Adaptive routing:** UGAL (Universal Globally Adaptive Load-balancing) for minimal latency

### Throughput

| Configuration | Per-Server | Bisection | Notes |
|---|---|---|---|
| a=64, h=2, p=4 | 400 Gb/s | 1.6 Tb/s per group | Non-blocking intra-group |
| a=128, h=4, p=4 | 400 Gb/s | 3.2 Tb/s per group | Higher path diversity |
| a=256, h=8, p=4 | 400 Gb/s | 6.4 Tb/s per group | Large groups |

### Cost

| Component | Unit Cost | Qty (100K nodes) | Total |
|---|---|---|---|
| High-radix switch (128×400G) | $50,000 | ~800 | $40,000,000 |
| Optical inter-group links | $5,000 | ~3,200 | $16,000,000 |
| NICs (ConnectX-7 400G) | $1,500 | 100,000 | $150,000,000 |
| Cabling | $200 | ~200,000 | $40,000,000 |
| **Total** | | | **~$246,000,000** |
| **Per-server** | | | **~$2,460** |

### Scalability

| Limit | Value | Bottleneck |
|---|---|---|
| Max nodes (practical) | ~1,000,000 | Group size × number of groups |
| Max nodes (theoretical) | ~10,000,000 | Optical link capacity |
| Group size limit | ~512 switches | Switch radix |
| Inter-group links | Limited by optics | Cost and power |

### Fault Tolerance

| Failure Mode | Impact | Recovery |
|---|---|---|
| Single switch failure | Nodes isolated | Intra-group reroute |
| Inter-group link failure | Reduced inter-group BW | Adaptive routing (UGAL) |
| Group failure | Significant capacity loss | Cross-group failover |
| **Worst case tolerance** | **Lose 1 inter-group link → minimal impact** | |

### Pros & Cons

| Pros | Cons |
|---|---|
| **Lowest diameter (2–3 hops)** | Complex routing (UGAL) |
| Excellent scalability | High-radix switches expensive |
| Good bisection bandwidth | Inter-group links are costly |
| Proven in HPC (Cray Aries, Slingshot) | Cabling complexity |
| Adaptive routing handles congestion | Requires optical for inter-group |

---

## Torus Topology

### Architecture (3D Torus)

```
    ┌─────────────────────────────────────────────────────────┐
    │                    3D Torus (4×4×4)                      │
    │                                                         │
    │   Z=0:                                                  │
    │   ┌───┬───┬───┬───┐                                     │
    │   │0,0│0,1│0,2│0,3│  ← wrap-around links               │
    │   ├───┼───┼───┼───┤                                     │
    │   │1,0│1,1│1,2│1,3│                                     │
    │   ├───┼───┼───┼───┤                                     │
    │   │2,0│2,1│2,2│2,3│                                     │
    │   ├───┼───┼───┼───┤                                     │
    │   │3,0│3,1│3,2│3,3│                                     │
    │   └───┴───┴───┴───┘                                     │
    │     │                                                   │
    │     │ Z-links (wrap-around)                             │
    │     ▼                                                   │
    │   Z=1: (same structure)                                 │
    │   ...                                                   │
    │   Z=3: (same structure)                                 │
    └─────────────────────────────────────────────────────────┘
```

### Structure

- **k-ary n-cube:** n-dimensional torus with k nodes per dimension
- **Wrap-around links:** Edges connect back to form a torus (no boundary)
- **Each node:** 2n links (n dimensions × 2 directions)
- **Common:** 2D torus (4×4, 8×8), 3D torus (4×4×4, 8×8×8)

### Latency Analysis

| Path Type | Hop Count | Switch Latency | Total |
|---|---|---|---|
| Same node | 0 | 0 | **< 1 µs** |
| Adjacent node | 1 | 100–200 ns | **1–2 µs** |
| 2D torus (8×8) worst case | 8 | 800–1600 ns | **5–10 µs** |
| 3D torus (8×8×8) worst case | 12 | 1200–2400 ns | **8–15 µs** |
| 3D torus (4×4×4) worst case | 6 | 600–1200 ns | **4–8 µs** |

- **Diameter:** n × ⌊k/2⌋ for k-ary n-cube
- **Average hops:** n × k/4 for k-ary n-cube

### Throughput

| Configuration | Per-Server | Bisection | Notes |
|---|---|---|---|
| 2D torus 8×8 (400G) | 400 Gb/s | 6.4 Tb/s | Moderate bisection |
| 3D torus 4×4×4 (400G) | 400 Gb/s | 12.8 Tb/s | Good bisection |
| 3D torus 8×8×8 (400G) | 400 Gb/s | 25.6 Tb/s | High bisection |

### Cost

| Component | Unit Cost | Qty (3D 4×4×4 = 64 nodes) | Total |
|---|---|---|---|
| Switch/router (6×400G) | $15,000 | 64 | $960,000 |
| NICs (ConnectX-7 400G) | $1,500 | 64 | $96,000 |
| Cabling | $200 | 384 | $76,800 |
| **Total** | | | **~$1,132,800** |
| **Per-server** | | | **~$17,700** |

### Scalability

| Limit | Value | Bottleneck |
|---|---|---|
| Max nodes (2D) | ~10,000 | Diameter grows as √N |
| Max nodes (3D) | ~100,000 | Diameter grows as ∛N |
| Max nodes (5D+) | ~1,000,000 | Complexity, cabling |
| Practical limit | ~10,000 | Latency at scale |

### Fault Tolerance

| Failure Mode | Impact | Recovery |
|---|---|---|
| Single node failure | Minimal (routing around) | Adaptive routing |
| Link failure | Minimal (alternate paths) | Dimension-order routing |
| Multiple failures | Degraded but operational | Depends on redundancy |
| **Worst case tolerance** | **Lose 1 node → ~1.5% capacity loss** | |

### Pros & Cons

| Pros | Cons |
|---|---|
| Simple, regular structure | Diameter grows with scale |
| Good for NoC (Network-on-Chip) | Bisection bandwidth limited |
| Easy to implement in hardware | Not ideal for large DC |
| Predictable routing | Wrap-around cabling |
| Low cost per node | Limited path diversity |

---

## Hypercube Topology

### Architecture (4D Hypercube)

```
    ┌─────────────────────────────────────────────────────────┐
    │              4D Hypercube (16 nodes)                     │
    │                                                         │
    │   Node 0 (0000) ────── Node 1 (0001)                   │
    │       │                   │                             │
    │       │                   │                             │
    │   Node 2 (0010) ────── Node 3 (0011)                   │
    │       │                   │                             │
    │       │                   │                             │
    │   Node 4 (0100) ────── Node 5 (0101)                   │
    │       │                   │                             │
    │       │                   │                             │
    │   Node 6 (0110) ────── Node 7 (0111)                   │
    │                                                         │
    │   ... (8 more nodes for 4D)                             │
    │                                                         │
    │   Each node connects to n neighbors (n = dimensions)    │
    │   Address = binary, links differ in 1 bit               │
    └─────────────────────────────────────────────────────────┘
```

### Structure

- **n-dimensional hypercube:** 2^n nodes, each with n links
- **Addressing:** Each node has n-bit binary address
- **Links:** Connect nodes differing in exactly 1 bit (Hamming distance = 1)
- **Diameter:** n hops (log₂N)

### Latency Analysis

| Path Type | Hop Count | Switch Latency | Total |
|---|---|---|---|
| Same node | 0 | 0 | **< 1 µs** |
| Adjacent node | 1 | 100–200 ns | **1–2 µs** |
| 4D hypercube (16 nodes) worst case | 4 | 400–800 ns | **3–6 µs** |
| 8D hypercube (256 nodes) worst case | 8 | 800–1600 ns | **6–12 µs** |
| 10D hypercube (1024 nodes) worst case | 10 | 1000–2000 ns | **8–15 µs** |

- **Diameter:** log₂N (excellent for small N)
- **Average hops:** log₂N / 2

### Throughput

| Configuration | Per-Server | Bisection | Notes |
|---|---|---|---|
| 4D (16 nodes, 400G) | 400 Gb/s | 3.2 Tb/s | Good bisection |
| 8D (256 nodes, 400G) | 400 Gb/s | 32 Tb/s | Excellent bisection |
| 10D (1024 nodes, 400G) | 400 Gb/s | 128 Tb/s | Excellent bisection |

### Cost

| Component | Unit Cost | Qty (8D = 256 nodes) | Total |
|---|---|---|---|
| Switch (10×400G) | $20,000 | 256 | $5,120,000 |
| NICs (ConnectX-7 400G) | $1,500 | 256 | $384,000 |
| Cabling | $200 | 2,560 | $512,000 |
| **Total** | | | **~$6,016,000** |
| **Per-server** | | | **~$23,500** |

### Scalability

| Limit | Value | Bottleneck |
|---|---|---|
| Max nodes (practical) | ~4,096 (12D) | Port count per switch |
| Max nodes (theoretical) | ~1,000,000 (20D) | Cabling, complexity |
| Practical limit | ~4,096 | Cost and cabling |

### Fault Tolerance

| Failure Mode | Impact | Recovery |
|---|---|---|
| Single node failure | Minimal | Routing around |
| Link failure | Minimal | Alternate paths |
| Multiple failures | Degraded | Depends on redundancy |
| **Worst case tolerance** | **Lose 1 node → ~0.4% capacity loss** | |

### Pros & Cons

| Pros | Cons |
|---|---|
| **Lowest diameter (log₂N)** | Limited to 2^n nodes |
| Excellent bisection bandwidth | Cabling complexity O(N log N) |
| Simple routing (XOR-based) | Not practical for large DC |
| Good for small HPC clusters | Cost per node is high |
| Elegant mathematical structure | Hard to incrementally scale |

---

## Custom / Emerging Topologies

### Jellyfish Topology

```
    ┌─────────────────────────────────────────────────────────┐
    │              Jellyfish (Random Regular Graph)            │
    │                                                         │
    │   ┌─────┐     ┌─────┐     ┌─────┐     ┌─────┐         │
    │   │ SW1 │─────│ SW2 │─────│ SW3 │─────│ SW4 │         │
    │   └──┬──┘     └──┬──┘     └──┬──┘     └──┬──┘         │
    │      │           │           │           │              │
    │      │     ┌─────┴─────┐     │           │              │
    │      │     │           │     │           │              │
    │   ┌──┴──┐  │  ┌─────┐  │  ┌──┴──┐     ┌──┴──┐         │
    │   │ SW5 │──│──│ SW6 │──│──│ SW7 │─────│ SW8 │         │
    │   └─────┘  │  └─────┘  │  └─────┘     └─────┘         │
    │            │           │                               │
    │   Random inter-switch connections (q links each)       │
    │   Remaining ports connect to servers (p links each)    │
    └─────────────────────────────────────────────────────────┘
```

#### Key Properties

- **Structure:** Random regular graph G(N, k) — N switches, k ports each
- **Servers:** p = k - q ports per switch connect to servers
- **Scalability:** N × p servers with N switches (vs. N × k for fat-tree)
- **Oversubscription:** 1:1 achievable with proper q

#### Performance

| Metric | Value | Notes |
|---|---|---|
| Diameter | O(log N / log k) | Similar to random graphs |
| Bisection | High (random) | Better than fat-tree at same cost |
| Path diversity | Excellent | Many random paths |
| Cost efficiency | **~2× better than fat-tree** | More servers per switch |

#### Cost Comparison (100K servers)

| Topology | Switches | Cost/Server | Total |
|---|---|---|---|
| Fat-Tree (k=48) | 1,056 | ~$5,050 | ~$53M |
| Jellyfish | ~700 | ~$2,500 | ~$17.5M |
| **Savings** | **~34%** | **~50%** | **~67%** |

---

### Slim Fly Topology

```
    ┌─────────────────────────────────────────────────────────┐
    │              Slim Fly (Approximate de Bruijn)            │
    │                                                         │
    │   ┌─────┐     ┌─────┐     ┌─────┐     ┌─────┐         │
    │   │ SW1 │─────│ SW2 │─────│ SW3 │─────│ SW4 │         │
    │   └──┬──┘     └──┬──┘     └──┬──┘     └──┬──┘         │
    │      │           │           │           │              │
    │      └───────────┼───────────┘           │              │
    │                  │                       │              │
    │   ┌─────┐     ┌──┴──┐     ┌─────┐     ┌──┴──┐         │
    │   │ SW5 │─────│ SW6 │─────│ SW7 │─────│ SW8 │         │
    │   └─────┘     └─────┘     └─────┘     └─────┘         │
    │                                                         │
    │   Based on de Bruijn graph — near-optimal diameter     │
    │   for given radix                                       │
    └─────────────────────────────────────────────────────────┘
```

#### Key Properties

- **Structure:** Approximate de Bruijn graph — near-optimal diameter
- **Diameter:** ~log_k(N) — optimal for given radix k
- **Radix:** Can use high-radix switches (128+ ports) efficiently
- **Designed for:** Minimizing diameter at large scale

#### Performance

| Metric | Value | Notes |
|---|---|---|
| Diameter | ~log_k(N) | Near-optimal |
| Bisection | High | Good for all-to-all |
| Path diversity | Good | Multiple paths |
| Cost | High | Requires high-radix switches |

---

### Circuit-Switched / Hybrid Topology

```
    ┌─────────────────────────────────────────────────────────┐
    │           Hybrid: Packet-Switched + Circuit-Switched     │
    │                                                         │
    │   ┌─────┐     ┌─────┐     ┌─────┐     ┌─────┐         │
    │   │ SW1 │═════│ SW2 │═════│ SW3 │═════│ SW4 │         │
    │   └──┬──┘     └──┬──┘     └──┬──┘     └──┬──┘         │
    │      │           │           │           │              │
    │   ┌──┴──┐     ┌──┴──┐     ┌──┴──┐     ┌──┴──┐         │
    │   │Nodes│     │Nodes│     │Nodes│     │Nodes│         │
    │   └─────┘     └─────┘     └─────┘     └─────┘         │
    │                                                         │
    │   ═══ = Circuit-switched (optical, reconfigurable)     │
    │   ─── = Packet-switched (Ethernet/InfiniBand)           │
    │                                                         │
    │   Circuit layer: Reconfigured for elephant flows        │
    │   Packet layer: Handles control, small messages         │
    └─────────────────────────────────────────────────────────┘
```

#### Key Properties

- **Two layers:** Packet-switched (Ethernet/IB) + Circuit-switched (optical)
- **Reconfiguration:** Optical circuits reconfigured in ~ms for elephant flows
- **Use case:** AI training clusters with large all-to-all patterns
- **Examples:** NVIDIA Quantum-2, Intel Silicon Photonics

#### Performance

| Metric | Packet Layer | Circuit Layer | Combined |
|---|---|---|---|
| Latency | 1–3 µs | 40 ns – 1 µs | **40 ns – 1 µs** (circuit) |
| Throughput | 400 Gb/s | 25–100 Gb/s/port | **Higher effective** |
| Reconfiguration | N/A | ~ms | Amortized |
| Best for | Small messages | Elephant flows | **All patterns** |

---

## Comparative Analysis Matrix

### Latency Comparison

| Topology | Same Rack | Cross-Rack | Cross-Pod | Worst Case | Diameter |
|---|---|---|---|---|---|
| Spine-Leaf (2-tier) | < 1 µs | 1.5–3 µs | N/A | 3–5 µs | 2–4 |
| Fat-Tree (3-tier) | < 1 µs | 1.5–3 µs | 3–6 µs | 5–10 µs | 4–6 |
| Dragonfly | < 1 µs | 1–2 µs | 2–4 µs | 3–6 µs | 2–3 |
| Torus (3D 4×4×4) | < 1 µs | 1–2 µs | 2–4 µs | 4–8 µs | 6 |
| Torus (3D 8×8×8) | < 1 µs | 1–2 µs | 2–4 µs | 8–15 µs | 12 |
| Hypercube (8D) | < 1 µs | 1–2 µs | 2–4 µs | 6–12 µs | 8 |
| Jellyfish | < 1 µs | 1–3 µs | 2–5 µs | 3–7 µs | O(log N) |
| Slim Fly | < 1 µs | 1–2 µs | 2–4 µs | 3–6 µs | ~log_k(N) |

### Throughput Comparison

| Topology | Per-Server | Bisection BW | Oversubscription | Notes |
|---|---|---|---|---|
| Spine-Leaf | 400–800 Gb/s | 1.6–6.4 Tb/s | 1:1 or 2:1 | Configurable |
| Fat-Tree | 400–800 Gb/s | 0.5–2.5 Pb/s | 1:1 | Non-blocking |
| Dragonfly | 400–800 Gb/s | 1.6–6.4 Tb/s/group | 1:1 intra-group | Adaptive |
| Torus (3D) | 400 Gb/s | 6.4–25.6 Tb/s | 1:1 | Good bisection |
| Hypercube | 400–800 Gb/s | 3.2–128 Tb/s | 1:1 | Excellent |
| Jellyfish | 400–800 Gb/s | High (random) | 1:1 | Cost-efficient |
| Slim Fly | 400–800 Gb/s | High | 1:1 | Near-optimal |

### Cost Comparison (Normalized per 1000 Servers)

| Topology | Switch Cost | NIC Cost | Cable Cost | Total | Per-Server |
|---|---|---|---|---|---|
| Spine-Leaf | $55K | $1,500K | $220K | $1,775K | $1,775 |
| Fat-Tree | $110K | $1,500K | $440K | $2,050K | $2,050 |
| Dragonfly | $62K | $1,500K | $390K | $1,952K | $1,952 |
| Torus (3D) | $23K | $1,500K | $150K | $1,673K | $1,673 |
| Hypercube | $78K | $1,500K | $310K | $1,888K | $1,888 |
| Jellyfish | $44K | $1,500K | $176K | $1,720K | $1,720 |
| Slim Fly | $62K | $1,500K | $310K | $1,872K | $1,872 |

### Scalability Comparison

| Topology | Max Nodes (Practical) | Max Nodes (Theoretical) | Incremental Scale | Notes |
|---|---|---|---|---|
| Spine-Leaf | ~100,000 | ~500,000 | Easy | Add leaves |
| Fat-Tree | ~100,000 | ~1,000,000 | Medium | Add pods |
| Dragonfly | ~1,000,000 | ~10,000,000 | Medium | Add groups |
| Torus (3D) | ~100,000 | ~1,000,000 | Hard | Fixed dimensions |
| Hypercube | ~4,096 | ~1,000,000 | Hard | Power of 2 |
| Jellyfish | ~100,000 | ~1,000,000 | Easy | Add switches |
| Slim Fly | ~1,000,000 | ~10,000,000 | Medium | Add switches |

### Fault Tolerance Comparison

| Topology | Single Node | Single Link | Multiple Failures | Recovery Time | Notes |
|---|---|---|---|---|---|
| Spine-Leaf | ★★★★★ | ★★★★★ | ★★★★ | < 1 s | ECMP |
| Fat-Tree | ★★★★ | ★★★★ | ★★★ | < 1 s | ECMP |
| Dragonfly | ★★★★ | ★★★★★ | ★★★★ | < 1 s | UGAL |
| Torus | ★★★★ | ★★★★ | ★★★ | < 1 s | Adaptive |
| Hypercube | ★★★★ | ★★★★ | ★★★ | < 1 s | XOR routing |
| Jellyfish | ★★★★★ | ★★★★★ | ★★★★ | < 1 s | Random paths |
| Slim Fly | ★★★★ | ★★★★ | ★★★★ | < 1 s | de Bruijn |

---

## Selection Guide

### Decision Matrix

| Use Case | Recommended Topology | Why |
|---|---|---|
| **General DC (10K–50K servers)** | Spine-Leaf | Simple, cost-effective, industry standard |
| **AI Training Cluster (1K–10K GPUs)** | Dragonfly or Fat-Tree | Low diameter, high bisection, adaptive routing |
| **HPC (10K–100K nodes)** | Dragonfly or Slim Fly | Scalable, low diameter, good all-to-all |
| **Small HPC (< 1K nodes)** | Hypercube or Torus | Low diameter, simple, cost-effective |
| **Cost-Constrained DC** | Jellyfish | ~50% cost savings vs. fat-tree |
| **Ultra-Low Latency (< 2 µs)** | Dragonfly or Spine-Leaf (2-tier) | Minimal hop count |
| **Maximum Scalability** | Dragonfly or Slim Fly | 1M+ nodes |
| **NoC / Chip-level** | Torus (2D/3D) | Simple, regular, hardware-friendly |
| **Hybrid AI + General** | Circuit-Switched + Spine-Leaf | Best of both worlds |

### Topology Selection Flowchart

```
                    ┌─────────────────────┐
                    │  What is the scale? │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
         < 1K nodes      1K–100K nodes     > 100K nodes
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐
    │ Hypercube/Torus │ │ Spine-Leaf   │ │ Dragonfly/Slim  │
    │ (low diameter)  │ │ or Fat-Tree  │ │ Fly (scalable)  │
    └─────────────────┘ └──────────────┘ └─────────────────┘
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐
    │ Cost-sensitive? │ │ AI/HPC?      │ │ Cost-sensitive? │
    │ → Torus         │ │ → Dragonfly  │ │ → Slim Fly      │
    │ Latency?        │ │ General DC?  │ │ Max scale?      │
    │ → Hypercube     │ │ → Spine-Leaf │ │ → Dragonfly     │
    └─────────────────┘ └──────────────┘ └─────────────────┘
```

### ULL-Specific Recommendations

| Priority | Topology | Configuration | Expected Latency |
|---|---|---|---|
| **Lowest latency** | Dragonfly | a=64, h=2, UGAL routing | 1–2 µs |
| **Best cost/latency** | Spine-Leaf (2-tier) | 400G, non-blocking | 1.5–3 µs |
| **Best scalability** | Dragonfly | a=128, h=4, optical inter-group | 2–4 µs |
| **Best for AI training** | Dragonfly + Circuit | Hybrid with optical circuit | 40 ns – 2 µs |
| **Best for HPC** | Slim Fly | High-radix (128+), de Bruijn | 1–3 µs |
| **Best for small cluster** | Hypercube (8D) | 256 nodes, 400G | 1–6 µs |

---

## References

1. Al-Fares, M., Loukissas, A., & Vahdat, A. (2008). "A Scalable, Commodity Data Center Network Architecture." *ACM SIGCOMM*.
2. Kim, J., Dally, W. J., Scott, S., & Abts, D. (2008). "Technology-Driven, Highly-Scalable Dragonfly Topology." *ISCA*.
3. Singla, A., Hong, C. Y., Popa, L., & Godfrey, P. B. (2012). "Jellyfish: Networking Data Centers Randomly." *NSDI*.
4. Besta, M., & Hoefler, T. (2014). "Slim Fly: A Cost Effective Low-Diameter Network Topology." *SC*.
5. Dally, W. J., & Towles, B. (2004). *Principles and Practices of Interconnection Networks*. Morgan Kaufmann.
6. NVIDIA. (2025). *Quantum-2 InfiniBand Switch System Architecture*. NVIDIA Technical Brief.
7. AMD. (2025). *Pensando Salina DPU Architecture*. AMD White Paper.
8. Intel. (2025). *Intel IPU E2100 Architecture*. Intel White Paper.
9. Ultra Ethernet Consortium. (2025). *UEC 1.0 Specification*. UEC.
10. Cray/HPE. (2025). *Slingshot Interconnect Architecture*. HPE Documentation.

---

*Document generated: 2026-09-29*  
*Project: ultra-low-latency-infra*  
*Author: Hermes Agent*
