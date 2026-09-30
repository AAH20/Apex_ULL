# ULL Colocation Architecture Pattern

**Project:** ultra-low-latency-infra  
**Date:** 2026-09-29  
**Scope:** Exchange colocation, proximity hosting, cloud regions, edge computing  
**Metrics:** Latency, throughput, cost, availability, regulatory

---

## Table of Contents

1. [Pattern Overview](#1-pattern-overview)
2. [Exchange Colocation](#2-exchange-colocation)
3. [Proximity Hosting](#3-proximity-hosting)
4. [Cloud Regions](#4-cloud-regions)
5. [Edge Computing](#5-edge-computing)
6. [Comparative Analysis](#6-comparative-analysis)
7. [Decision Framework](#7-decision-framework)
8. [Reference Architecture](#8-reference-architecture)
9. [Sources](#9-sources)

---

## 1. Pattern Overview

Ultra-low-latency (ULL) colocation is the practice of placing compute infrastructure in physical proximity to data sources, exchanges, or end users to minimize network propagation delay. In 2026, the physics remain immutable: light in fiber travels at ~67% of *c*, light in air at ~99% of *c*, and every millimeter of trace adds picoseconds. The architecture pattern is a **tiered proximity model** — from nanoseconds (same rack) to milliseconds (cross-continent) — where each tier trades cost, availability, and regulatory complexity for latency reduction.

### Latency Tiers at a Glance

| Tier | Distance | Propagation Latency | Typical Use Case |
|------|----------|---------------------|------------------|
| Intra-rack | <1 m | <10 ns | FPGA feed handler ↔ strategy engine |
| Intra-building | <100 m | <500 ns | Cross-connect to exchange matching engine |
| Metro | <50 km | <250 μs | Proximity hosting, backup site |
| Regional | <500 km | <2.5 ms | Cloud region, disaster recovery |
| Continental | <3,000 km | <15 ms | Cross-region replication, analytics |
| Intercontinental | >5,000 km | >50 ms | Global anycast, non-latency-critical |

### Core Design Principles

1. **Physics first** — No software optimization can beat propagation delay. Location is the primary latency lever.
2. **Determinism over average** — A 500 ns average with 600 ns tail beats a 200 ns average with 50 μs tail. Colocation must guarantee consistent latency, not just low mean.
3. **Path diversity** — Single fiber path = single point of failure. Diverse physical entries and media (fiber + microwave) are mandatory for availability.
4. **Regulatory gravity** — Data sovereignty, financial regulation, and spectrum licensing constrain colocation choices as much as physics.

---

## 2. Exchange Colocation

### 2.1 Description

Exchange colocation places trading systems in the same data center as an exchange's matching engine, connected via ultra-short physical cross-connects. This is the lowest-latency tier available to non-exchange participants and the foundation of modern HFT infrastructure.

### 2.2 Latency

| Component | Latency | Notes |
|-----------|---------|-------|
| Matching engine (CME, NYSE, Nasdaq) | ~10 μs | Gateway round-trip <100 μs |
| Cross-connect (same rack/cage) | 50–200 ns | Passive fiber, minimal switching |
| FPGA feed handler → strategy | 150–500 ns | Full FPGA tick-to-trade |
| Kernel bypass (DPDK/Onload) | 1–5 μs | Software strategy path |
| Standard kernel stack | 10–50 μs | Non-latency-critical monitoring |

**Key insight:** The cross-connect itself contributes negligible latency (<200 ns). The dominant cost is the strategy execution path — FPGA vs. kernel bypass vs. standard stack. Colocation eliminates the *network* latency; the *compute* latency is a separate optimization.

**Tick-to-trade latency hierarchy (2026):**

| Implementation | Typical Latency | Jitter | Use Case |
|---------------|----------------|--------|----------|
| Full FPGA tick-to-trade | 150–500 ns | Very low, deterministic | Simple, well-defined hot path |
| FPGA feed handler + CPU strategy | 100 ns – ~1 μs | Low on fast path | Fast hardware trigger, complex decision in software |
| Kernel bypass (Onload, DPDK) | 1–5 μs | Moderate | Most latency-sensitive strategies |
| Standard kernel network stack | 10–50 μs | High | Research, non-latency-bound |

### 2.3 Throughput

| Metric | Value | Context |
|--------|-------|---------|
| Market data (ITCH/OUCH) | 100M+ msg/s | Single FPGA feed handler |
| Order capacity | 150K–1M+ orders/s | FPGA-based systems |
| Cross-connect bandwidth | 10–100 Gb/s | Dedicated fiber pair |
| Exchange gateway | <100 μs round-trip | CME Globex, NYSE Pillar, Nasdaq INET |

### 2.4 Cost

| Cost Component | Range | Notes |
|----------------|-------|-------|
| Colocation cage (42U) | $5K–$25K/month | Varies by exchange, power density |
| Cross-connect | $500–$5K/month | Same-cage vs. cross-building |
| Power (per kW) | $200–$500/month | 10–30 kW typical for HFT rack |
| FPGA NIC (Solarflare/Exablaze) | $2K–$10K one-time | Kernel bypass capable |
| FPGA development | $500K–$2M+ | NRE for custom feed handler |
| **Total annual (single site)** | **$200K–$1M+** | Excludes strategy development |

**Industry reference:** Citadel Securities operates 50+ colocation sites globally with Equinix. Jump Trading added 12 new colocation data centers across NA, Europe, and Asia (2024–2026). Optiver maintains 16 data centers with ~75,000 km of fiber.

### 2.5 Availability

| Aspect | Target | Mechanism |
|--------|--------|-----------|
| Uptime | 99.99% | Dual power feeds, UPS, generator backup |
| Network redundancy | 99.999% | Diverse fiber paths, dual entry points |
| Failover | <1 s | Hot-standby FPGA, automatic order cancellation |
| Disaster recovery | <5 min | Proximity hosting site (Section 3) |

**Critical availability patterns:**
- **Dual colocation:** Primary at exchange, secondary at proximity hosting site 5–20 km away
- **Path diversity:** Minimum two physically separate fiber routes into the data center
- **Automatic reroute:** Fiber cut detection and sub-second failover to backup path (Optiver model)
- **Order cancellation:** On disconnect, all open orders cancelled to prevent orphaned positions

### 2.6 Regulatory

| Regulation | Scope | Impact on Colocation |
|------------|-------|---------------------|
| SEC Rule 15c3-5 (Market Access Rule) | US equities | Pre-trade risk checks required; colocated systems must integrate compliance |
| MiFID RTS 6 | EU trading | Algorithm testing, kill switches, market abuse surveillance |
| CME/NYSE membership rules | Exchange-specific | Colocation agreements subject to exchange approval and audit |
| Data localization (GDPR, etc.) | Cross-border | Market data may be subject to transfer restrictions |
| FINRA 4370 (Business Continuity) | US broker-dealers | DR site required; colocation failover must be tested |

**Key regulatory considerations:**
- Exchanges audit colocated participants for fair access and market integrity
- Co-sited systems must not create information asymmetry that violates market rules
- Cross-border colocation triggers data sovereignty requirements (e.g., EU market data in EU colocation)
- Regulatory reporting (CAT, MiFID II) must be maintained even during failover events

---

## 3. Proximity Hosting

### 3.1 Description

Proximity hosting places infrastructure in data centers 5–50 km from the exchange — close enough for single-digit millisecond latency via dedicated fiber or microwave, but with lower cost, more space, and better availability than exchange colocation. It serves as both a cost-effective primary site for less latency-sensitive strategies and a disaster recovery site for exchange-colocated systems.

### 3.2 Latency

| Medium | Chicago ↔ NY | Notes |
|--------|-------------|-------|
| Fiber optic | ~7.2 ms | ~67 of *c* (index of refraction) |
| Microwave wireless | ~4.7 ms | ~99 of *c* (through air) |
| **Advantage** | **~2.5 ms saved** | **~50 faster than fiber** |

**Metro proximity hosting (5–50 km from exchange):**

| Distance | Fiber Latency | Microwave Latency | Use Case |
|----------|--------------|-------------------|----------|
| 5 km | 25 μs | 15 μs | DR site, backup matching |
| 20 km | 100 μs | 60 μs | Proximity compute |
| 50 km | 250 μs | 150 μs | Regional aggregation |

**Key insight:** For metro distances, the latency difference between fiber and microwave is negligible (both sub-millisecond). The choice is driven by cost, reliability, and throughput — not latency. Microwave's advantage is primarily on long-haul routes (Chicago–NY, London–Frankfurt).

### 3.3 Throughput

| Metric | Fiber | Microwave | Notes |
|--------|-------|-----------|-------|
| Bandwidth | 100–400 Gb/s | 1–10 Gb/s | Microwave is bandwidth-limited |
| Leased wavelength | 100 Gb/s dedicated | N/A | Optiver model: 100 Gb/s trading WAN lines |
| Message rate | 100M+ msg/s | 10M+ msg/s | Microwave sufficient for order flow |
| Path diversity | Multiple fibers | Multiple towers | Both support redundancy |

**Industry reference:** Optiver leases wavelength services on long-distance fiber (dedicated lanes, 100 Gbps) with physical path diversity and automatic reroute on fiber cut. Jump Trading's subsidiary World Class Wireless operates custom microwave/millimeter-wave networks with towers across key routes.

### 3.4 Cost

| Cost Component | Range | Notes |
|----------------|-------|-------|
| Proximity hosting rack | $2K–$10K/month | 50–80% cheaper than exchange colocation |
| Leased fiber (metro) | $5K–$50K/month | Dedicated wavelength, 100 Gb/s |
| Microwave route | $1M–$10M+/year | Single long-haul route can exceed $10M/year |
| Build vs. lease | $5M–$50M capital | Building own microwave network |
| **Total annual (metro site)** | **$100K–$500K** | vs. $200K–$1M+ for exchange colocation |

**Cost comparison:**

| Model | Annual Cost | Latency to Exchange | Best For |
|-------|-------------|---------------------|----------|
| Exchange colocation | $200K–$1M+ | <100 μs | Ultra-low-latency strategies |
| Proximity hosting (fiber) | $100K–$500K | 25–250 μs | Mid-latency strategies, DR |
| Proximity hosting (microwave) | $500K–$2M+ | 15–150 μs | Long-haul advantage routes |
| Cloud region | $50K–$200K | 1–10 ms | Non-latency-critical, analytics |

### 3.5 Availability

| Aspect | Exchange Colocation | Proximity Hosting |
|--------|--------------------|-------------------|
| Power reliability | Tier III+ (99.982%) | Tier II–III (99.741–99.982%) |
| Network redundancy | Exchange-managed | Self-managed, more control |
| Physical security | Exchange facility | Varies by provider |
| Geographic diversity | Single point | Can be 5–50 km away |
| DR role | Primary | Secondary/tertiary |

**Availability patterns:**
- **Active-active:** Both sites process orders simultaneously, with position synchronization
- **Active-standby:** Proximity site takes over on exchange colocation failure (<5 min RTO)
- **Tiered strategies:** Ultra-low-latency at exchange, medium-latency at proximity, research in cloud

### 3.6 Regulatory

| Consideration | Impact |
|---------------|--------|
| Same jurisdiction | Proximity hosting in same metro avoids cross-border data issues |
| Cross-border proximity | Triggers data sovereignty (e.g., EU data must stay in EU) |
| Microwave spectrum | Licensed spectrum required; regulatory approval for tower construction |
| Financial regulation | Same rules as exchange colocation (SEC, MiFID, etc.) |
| Tax implications | Different metro = different tax jurisdiction |

---

## 4. Cloud Regions

### 4.1 Description

Cloud regions provide scalable, on-demand compute and storage in managed data centers. While not designed for ultra-low latency, they serve as the aggregation, analytics, and non-latency-critical tier in a ULL architecture. Cloud regions are essential for research, backtesting, risk management, and regulatory reporting.

### 4.2 Latency

| Path | Latency | Notes |
|------|---------|-------|
| Within same region (AZ to AZ) | 0.5–2 ms | Intra-region VPC |
| Cross-region (same continent) | 10–50 ms | AWS us-east-1 ↔ us-west-2: ~60 ms |
| Cross-continent | 50–150 ms | US ↔ Europe: ~80 ms |
| Cloud to exchange | 1–10 ms | Via Direct Connect/ExpressRoute |
| Cloud to proximity hosting | 5–20 ms | Via dedicated interconnect |

**Key insight:** Cloud latency is 100–1000× higher than colocation. A 100 ns FPGA tick-to-trade becomes 1–10 ms in the cloud — a 10,000× penalty. Cloud is unsuitable for latency-critical paths but essential for everything else.

**Cloud interconnect options:**

| Service | Latency | Bandwidth | Cost Model |
|---------|---------|-----------|------------|
| AWS Direct Connect | 1–5 ms | 1–100 Gb/s | Port + data transfer |
| Azure ExpressRoute | 1–5 ms | 50 Mb/s–100 Gb/s | Circuit + data transfer |
| Google Cloud Interconnect | 1–5 ms | 10–100 Gb/s | VLAN attachment + data transfer |
| Equinix Fabric | <1 ms (metro) | 1–100 Gb/s | Virtual connection |

### 4.3 Throughput

| Metric | Cloud Capability | Notes |
|--------|-----------------|-------|
| Compute | 100K+ vCPUs on-demand | Burstable, not sustained |
| Storage | 100M+ IOPS (io2 Block Express) | NVMe-backed |
| Network | 100 Gb/s per instance | Enhanced networking required |
| Data transfer | 10+ Tb/s aggregate | Egress costs dominate |
| Kafka/streaming | 1M+ msg/s | Managed MSK/Confluent |

**Throughput comparison:**

| Workload | Colocation | Cloud | Ratio |
|----------|-----------|-------|-------|
| Market data ingestion | 100M msg/s (FPGA) | 10M msg/s (software) | 10:1 |
| Order processing | 1M orders/s (FPGA) | 100K orders/s (CPU) | 10:1 |
| Research/backtesting | 100 cores dedicated | 10,000 cores burstable | Cloud wins |
| Storage IOPS | 10M+ (NVMe-oF) | 100M+ (cloud NVMe) | Cloud wins |

### 4.4 Cost

| Cost Component | Colocation | Cloud | Notes |
|----------------|-----------|-------|-------|
| Compute (per core/month) | $50–$150 | $30–$100 | Cloud cheaper at low utilization |
| Storage (per TB/month) | $100–$500 | $23–$250 | Cloud object storage cheapest |
| Network egress | $0 (internal) | $0.05–$0.12/GB | Cloud egress is major cost |
| Idle capacity | Wasted | Zero cost | Cloud wins for bursty workloads |
| **Steady-state (24/7)** | **$50K–$200K/month** | **$200K–$500K/month** | Colocation cheaper for sustained |
| **Bursty (10% utilization)** | **$50K–$200K/month** | **$20K–$50K/month** | Cloud cheaper for variable |

**Cost optimization patterns:**
- **Colocation for baseline:** Sustained 24/7 workloads in owned/colocated infrastructure
- **Cloud for burst:** Research, backtesting, and variable workloads on-demand
- **Cloud for storage:** Object storage for historical data, tick databases
- **Reserved instances:** 1–3 year commitments for predictable cloud workloads (40–60% discount)

### 4.5 Availability

| Aspect | Colocation | Cloud |
|--------|-----------|-------|
| SLA | Self-managed (99.99% achievable) | 99.95–99.99% (provider SLA) |
| AZ diversity | Self-deployed | Built-in (3+ AZs per region) |
| Region diversity | Self-deployed | Built-in (30+ regions globally) |
| DR complexity | High (self-managed) | Low (provider-managed) |
| Blast radius | Limited to your rack | Shared infrastructure (noisy neighbors) |

**Cloud availability patterns:**
- **Multi-AZ:** Active-active across 3 AZs in same region (99.99% SLA)
- **Multi-region:** Active-passive across regions (99.999% achievable)
- **Cloud + colocation:** Colocation for latency-critical, cloud for everything else

### 4.6 Regulatory

| Consideration | Impact |
|---------------|--------|
| Data residency | Cloud regions map to jurisdictions; choose region for compliance |
| Shared responsibility | Cloud provider secures infrastructure; you secure data and access |
| Financial services | AWS/Azure/GCP offer financial services clouds with enhanced compliance |
| Audit | Cloud providers maintain SOC 2, ISO 27001, PCI DSS, FedRAMP |
| Data sovereignty | EU data in EU regions; China data in China regions (separate cloud) |

---

## 5. Edge Computing

### 5.1 Description

Edge computing places compute at the network edge — cell towers, ISP points of presence, and on-premises micro data centers — to minimize latency for geographically distributed users. In ULL infrastructure, edge computing serves as the last-mile latency optimization for applications where the user (not the exchange) is the latency constraint.

### 5.2 Latency

| Edge Type | Distance | Latency | Use Case |
|-----------|----------|---------|----------|
| On-premises | <1 km | <10 μs | Factory automation, in-venue |
| Cell tower | 1–5 km | 50–200 μs | Mobile gaming, AR/VR |
| ISP PoP | 5–20 km | 250 μs–1 ms | Regional gaming, IoT |
| Metro edge | 20–50 km | 1–5 ms | City-scale applications |
| Regional edge | 50–200 km | 5–20 ms | State/province-scale |

**Edge vs. cloud latency:**

| Path | Latency | Notes |
|------|---------|-------|
| Device → edge (5G) | 1–10 ms | 5G UPF at edge |
| Device → cloud | 20–100 ms | Via internet backbone |
| Device → colocation | 50–200 ms | Via internet + exchange |

**Key insight:** Edge computing is the only tier where the latency constraint is the *user's* distance, not the exchange's. For HFT, edge is irrelevant (exchanges are fixed). For gaming, IoT, and AR/VR, edge is the primary latency lever.

### 5.3 Throughput

| Edge Type | Compute | Network | Notes |
|-----------|---------|---------|-------|
| Cell tower | 1–4 servers | 10–25 Gb/s | Space/power constrained |
| ISP PoP | 10–40 servers | 25–100 Gb/s | Moderate capacity |
| Metro edge | 40–200 servers | 100–400 Gb/s | Small data center |
| Regional edge | 200–2000 servers | 400 Gb/s+ | Full data center |

**Edge throughput comparison:**

| Workload | Edge Capability | Cloud Capability | Notes |
|----------|----------------|-----------------|-------|
| Real-time inference | 1–10 ms | 20–100 ms | Edge required for ULL |
| Video streaming | 10–50 ms | 50–200 ms | Edge CDN essential |
| Game state sync | 5–20 ms | 50–150 ms | Edge for competitive gaming |
| Batch analytics | Limited | Massive | Cloud wins |

### 5.4 Cost

| Cost Component | Edge | Cloud | Notes |
|----------------|------|-------|-------|
| Compute (per node) | $5K–$50K | $30–$100/core/month | Edge is capital-intensive |
| Real estate | $10K–$100K/month | Included | Edge requires physical space |
| Power/cooling | $500–$5K/month | Included | Edge requires dedicated infrastructure |
| Network | $1K–$50K/month | Egress fees | Edge requires backhaul |
| **Total TCO (5-year)** | **$500K–$5M** | **$100K–$1M** | Edge more expensive at small scale |

**Cost patterns:**
- **Edge is capital-intensive:** High upfront cost, low marginal cost per user
- **Cloud is operational:** Low upfront, high variable cost
- **Break-even:** Edge wins at scale (>10K users in a metro); cloud wins for distributed/low-density

### 5.5 Availability

| Aspect | Edge | Cloud |
|--------|------|-------|
| Redundancy | Self-managed (limited) | Built-in (multi-AZ, multi-region) |
| Failure domain | Single site | Provider-managed |
| Maintenance | On-site required | Remote, provider-managed |
| Scalability | Limited by physical space | Virtually unlimited |
| SLA | 99.9% (self-managed) | 99.95–99.99% (provider) |

**Edge availability patterns:**
- **Active-active metro:** Multiple edge sites in same metro, anycast routing
- **Edge + cloud failover:** Edge handles ULL; cloud takes over on edge failure
- **Hierarchical edge:** Metro edge → regional edge → cloud (graceful degradation)

### 5.6 Regulatory

| Consideration | Impact |
|---------------|--------|
| Data localization | Edge keeps data local; strong privacy posture |
| Spectrum licensing | 5G edge requires spectrum licenses |
| Physical security | Edge sites are less secure than data centers |
| Content delivery | Edge caching may trigger content licensing issues |
| IoT regulations | Edge IoT devices subject to device certification (FCC, CE) |

---

## 6. Comparative Analysis

### 6.1 Latency Comparison

| Tier | Latency to Exchange | Latency to User | Determinism | Best For |
|------|-------------------|-----------------|-------------|----------|
| Exchange colocation | <100 μs | N/A | Very high (ns) | HFT, market making |
| Proximity hosting | 25 μs–5 ms | N/A | High (μs) | Mid-latency trading, DR |
| Cloud region | 1–10 ms | 20–100 ms | Moderate (ms) | Research, analytics, reporting |
| Edge computing | N/A | 1–20 ms | High (μs–ms) | Gaming, IoT, AR/VR |

### 6.2 Throughput Comparison

| Tier | Market Data | Order Processing | Research Compute | Storage |
|------|------------|-----------------|-----------------|---------|
| Exchange colocation | 100M+ msg/s | 1M+ orders/s | 100 cores | 10M+ IOPS |
| Proximity hosting | 50M+ msg/s | 500K+ orders/s | 500 cores | 5M+ IOPS |
| Cloud region | 10M msg/s | 100K orders/s | 10,000+ cores | 100M+ IOPS |
| Edge computing | 1M msg/s | 10K orders/s | 50 cores | 1M+ IOPS |

### 6.3 Cost Comparison (Annual, Single Site)

| Tier | Capital | Operational | Total | Cost/Latency Ratio |
|------|---------|-------------|-------|-------------------|
| Exchange colocation | $500K–$2M | $200K–$1M | $700K–$3M | $7K–$30K per μs |
| Proximity hosting | $100K–$500K | $100K–$500K | $200K–$1M | $40–$4K per μs |
| Cloud region | $0 | $50K–$500K | $50K–$500K | $5–$50 per ms |
| Edge computing | $500K–$5M | $100K–$1M | $600K–$6M | N/A (user latency) |

### 6.4 Availability Comparison

| Tier | Uptime | RTO | RPO | Complexity |
|------|--------|-----|-----|------------|
| Exchange colocation | 99.99% | <1 s | 0 (synchronous) | High |
| Proximity hosting | 99.95% | <5 min | <1 s | Medium |
| Cloud region | 99.95–99.99% | <15 min | <1 min | Low |
| Edge computing | 99.9% | <1 min | <1 s | Medium |

### 6.5 Regulatory Comparison

| Tier | Data Sovereignty | Financial Regulation | Audit Complexity | Cross-Border |
|------|------------------|---------------------|-----------------|--------------|
| Exchange colocation | Same jurisdiction | Direct (SEC, MiFID) | High (exchange audit) | Complex |
| Proximity hosting | Same metro | Direct | Medium | Moderate |
| Cloud region | Region-dependent | Shared responsibility | Low (provider certs) | Simple (choose region) |
| Edge computing | Local | Varies | Medium | Simple (local) |

---

## 7. Decision Framework

### 7.1 When to Use Each Tier

```
┌─────────────────────────────────────────────────────────────────┐
│                    ULL Colocation Decision Tree                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Is latency to exchange <1 ms required?                         │
│  ├── YES → Exchange colocation (Section 2)                      │
│  │         └── Budget constrained? → Proximity hosting (3)      │
│  └── NO → Is latency to user <20 ms required?                   │
│            ├── YES → Edge computing (Section 5)                 │
│            └── NO → Is compute bursty or sustained?              │
│                      ├── Bursty → Cloud region (Section 4)      │
│                      └── Sustained → Proximity hosting (3)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Strategy-to-Tier Mapping

| Strategy Type | Latency Requirement | Recommended Tier | Annual Budget |
|---------------|-------------------|-----------------|---------------|
| Market making (equities) | <100 μs | Exchange colocation | $500K–$2M |
| Market making (options) | <500 μs | Exchange colocation | $500K–$2M |
| Statistical arbitrage | <1 ms | Exchange colocation + proximity | $300K–$1M |
| Momentum/trend following | <10 ms | Proximity hosting | $100K–$500K |
| Execution algorithms | <100 ms | Cloud region | $50K–$200K |
| Research/backtesting | Seconds | Cloud region | $20K–$100K |
| Risk management | Minutes | Cloud region | $10K–$50K |
| Regulatory reporting | Hours | Cloud region | $5K–$20K |

### 7.3 Hybrid Architecture Pattern

The optimal ULL architecture uses **all four tiers** in a tiered model:

```
┌──────────────────────────────────────────────────────────────────┐
│                    Tier 4: Cloud Regions                         │
│  Research │ Backtesting │ Risk │ Reporting │ ML Training        │
│  $50K–$500K/year │ 99.95% │ Multi-region                        │
├──────────────────────────────────────────────────────────────────┤
│                 Tier 3: Edge Computing                           │
│  Gaming │ IoT │ AR/VR │ Mobile inference                        │
│  $100K–$1M/year │ 99.9% │ Metro distribution                   │
├──────────────────────────────────────────────────────────────────┤
│              Tier 2: Proximity Hosting                           │
│  DR site │ Mid-latency strategies │ Aggregation                 │
│  $100K–$500K/year │ 99.95% │ 5–50 km from exchange             │
├──────────────────────────────────────────────────────────────────┤
│             Tier 1: Exchange Colocation                          │
│  HFT │ Market making │ Ultra-low-latency strategies             │
│  $200K–$1M+/year │ 99.99% │ Same building as matching engine   │
└──────────────────────────────────────────────────────────────────┘
```

### 7.4 Cost-Optimization Patterns

1. **Right-size the tier:** Don't pay for exchange colocation if proximity hosting meets latency requirements
2. **Burst to cloud:** Use cloud for research/backtesting; keep colocation for production
3. **Multi-site arbitrage:** Place latency-critical systems at exchange; everything else at cheapest tier
4. **Cloud reserved instances:** 1–3 year commitments for predictable cloud workloads (40–60% savings)
5. **Edge caching:** Cache at edge to reduce cloud egress costs (78% storage cost reduction with tiered storage)

---

## 8. Reference Architecture

### 8.1 Physical Layout

```
                    ┌─────────────────────┐
                    │   Exchange Data     │
                    │     Center          │
                    │  ┌───────────────┐  │
                    │  │  Matching     │  │
                    │  │  Engine       │  │
                    │  │  (~10 μs)     │  │
                    │  └───────┬───────┘  │
                    │          │          │
                    │  ┌───────┴───────┐  │
                    │  │  Cross-connect │  │
                    │  │  (<200 ns)     │  │
                    │  └───────┬───────┘  │
                    │          │          │
                    │  ┌───────┴───────┐  │
                    │  │  FPGA Feed    │  │
                    │  │  Handler      │  │
                    │  │  (150–500 ns) │  │
                    │  └───────┬───────┘  │
                    │          │          │
                    │  ┌───────┴───────┐  │
                    │  │  Strategy     │  │
                    │  │  Engine       │  │
                    │  │  (CPU/FPGA)   │  │
                    │  └───────────────┘  │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │  Diverse Fiber Paths │
                    │  (2+ physical routes)│
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────┴──────┐  ┌─────┴──────┐  ┌──────┴───────┐
    │  Proximity     │  │  Proximity │  │  Cloud       │
    │  Hosting A     │  │  Hosting B │  │  Region      │
    │  (5–20 km)     │  │  (20–50 km)│  │  (100+ km)   │
    │  $100K–$500K   │  │  $50K–$200K│  │  $50K–$500K  │
    │  99.95%        │  │  99.9%     │  │  99.95%      │
    └────────────────┘  └────────────┘  └──────────────┘
```

### 8.2 Network Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                     Network Topology                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Exchange DC ◄──── Microwave (4.7 ms) ────► Proximity A        │
│       │                                          │              │
│       └────── Fiber (7.2 ms) ────────────► Proximity B         │
│       │                                          │              │
│       └────── Dedicated WAN (100 Gb/s) ──────► Cloud Region    │
│       │                                          │              │
│       └────── Internet VPN ──────────────────► Edge Sites      │
│                                                                 │
│  Latency: Microwave < Fiber < WAN < Internet                    │
│  Cost: Microwave > Fiber > WAN > Internet                       │
│  Reliability: Fiber > Microwave > WAN > Internet                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Failure Modes and Mitigations

| Failure Mode | Impact | Mitigation | RTO |
|-------------|--------|------------|-----|
| Exchange colocation outage | Total trading halt | Failover to proximity hosting | <5 min |
| Fiber cut (single path) | Degraded connectivity | Automatic reroute to backup path | <1 s |
| Microwave outage (weather) | Loss of microwave route | Failover to fiber | <1 s |
| Proximity hosting outage | Loss of DR | Failover to cloud (degraded) | <15 min |
| Cloud region outage | Loss of analytics | Multi-region failover | <15 min |
| Edge site outage | Loss of local service | Failover to regional edge/cloud | <1 min |
| FPGA failure | Loss of feed handler | Hot-standby FPGA | <100 ms |
| Power outage (single feed) | Degraded power | Dual feed + UPS + generator | 0 s |

---

## 9. Sources

- [HFT Firms Research Report](../../reports/hft-firms.md) — §1 "Industry Context", §2–7 firm profiles
- [Network Technologies Research Report](../../reports/network-technologies.md) — §2 "RDMA", §4 "Kernel Bypass"
- [FPGA Technologies Research Report](../../reports/fpga-technologies.md) — §2–6 FPGA families, §8 "Comparative Analysis"
- [Payment Networks Research Report](../../reports/payment-networks.md) — §1–10 network profiles
- [Gaming Research Report](../../reports/gaming.md) — §1–6 platform profiles
- [Determinism Benchmarks](../../benchmarks/determinism/README.md) — Tier targets and measurement methodology
- [Throughput Evaluation Framework](../../evaluation/throughput/README.md) — Industry throughput ranges

---

*Document generated: 2026-09-29*  
*For updates, see the project repository: ultra-low-latency-infra*
