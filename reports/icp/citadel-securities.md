# ICP Research: Citadel Securities

**Date:** 2026-09-30
**Researcher:** AI Agent
**Status:** Complete

---

## Executive Summary

Citadel Securities is the largest market maker in the United States, executing approximately 25-30% of all US equity trades and ~40% of retail order flow. The firm posted a record **$12.2 billion in trading revenue in 2025** (up 25% from $9.7B in 2024), with **$6.5 billion EBITDA**. This is a technology-first firm where infrastructure latency directly determines profitability — microseconds matter.

---

## 1. Company Profile

| Attribute | Value |
|---|---|
| **Founded** | 2002 |
| **Founder/Chairman** | Kenneth C. Griffin |
| **CEO** | Peng Zhao (since 2017) |
| **Headquarters** | Miami, Florida |
| **Employees** | ~2,500 (≈1,800+ technologists/quants) |
| **Revenue (2025)** | $12.2 billion (record) |
| **EBITDA (2025)** | $6.5 billion |
| **Net Income (2024)** | $4.2 billion |
| **Equity Capital** | $15B+ |
| **Credit Access** | $50B+ |
| **Markets** | 50+ markets, 150+ venues globally |
| **Daily Volume** | $200B+ ADV, 50B+ shares/day peak |
| **Data Processed** | 2 PB/day |

---

## 2. Latency Requirements

Citadel Securities operates at the extreme end of low-latency trading infrastructure:

### Execution Latency Budget
- **Total trade execution window:** ~30 microseconds
  - **2 µs** — decision-making (alpha signal)
  - **5 µs** — risk check
  - **Few µs** — order routing/execution
- **Order routing target:** sub-10µs
- **Regional network latency:** sub-1ms
- **Median execution latency:** <100ms (retail-facing)
- **Tick-to-trade:** microsecond-scale for HFT strategies

### Latency Philosophy
From Citadel's own engineering blog:
> "You have 30 microseconds to execute a trade... If you miss your window, even by nanoseconds, someone else gets the fill. This is not a rare occurrence or an edge case. It happens billions of times per day."

Key principles:
- **Consistency at the tail end** of latency distributions (not average performance)
- **Reliability during burst conditions** (peak trading periods)
- **Deterministic behavior under stress**
- **Physical optimization**: memory layout, cache lines, NUMA architecture, core affinity, data movement through hardware

---

## 3. Technology Stack

### Core Infrastructure Technologies

| Layer | Technology |
|---|---|
| **Programming Language** | C++ (C++26 adoption for concurrency/execution evolution) |
| **Kernel Bypass** | DPDK, Solarflare OpenOnload, RDMA (RoCE/InfiniBand) |
| **FPGA Acceleration** | Custom FPGA solutions for market data decoding, order routing |
| **Smart NICs** | Exablaze/ExaNIC, Solarflare, Mellanox ConnectX |
| **Networking** | 200 Gbps advanced networking, Arista switches (<100ns latency) |
| **Interconnect** | Microwave towers, undersea cables, private fiber |
| **Cloud (Research)** | Google Cloud — 1M+ cores, TPU Ironwood, 200 Gbps interconnect |
| **Co-location** | 50+ sites globally (Equinix and others) |
| **CPU** | Intel Xeon Scalable (Ice Lake+), AMD EPYC |
| **Memory** | DDR4-3200 with HugePages, pre-allocated memory pools |
| **OS** | Linux (tuned, kernel-bypass capable) |

### Infrastructure Architecture
- **Private global network**: Chicago, New York, London, Hong Kong + 20+ major hubs
- **Co-location**: 50+ data centers globally
- **Cloud hybrid**: On-prem for latency-sensitive trading; Google Cloud for quantitative research
- **Research platform**: 1M+ cores on Google Cloud, TPU-based AI/ML workloads
- **Data infrastructure**: 2PB/day tick data processing, centralized data lakes

### Engineering Practices
- Lock-free data structures throughout
- CPU pinning and core isolation
- Zero-allocation critical paths (pre-allocated memory pools)
- Hardware timestamping (PTP precision, nanosecond-level)
- NUMA-aware design
- Cache-line optimization

---

## 4. Infrastructure Spend & Investment

### Annual Technology Investment

| Category | Estimated Spend |
|---|---|
| **Tech & R&D (total)** | $500M – $800M |
| **Hardware/R&D** | $200M – $300M |
| **Infrastructure & Security** | ~$500M |
| **Capex (market-making tech + data centers)** | $1.2B+ |
| **Compliance-related tech** | $550M – $650M |
| **Senior engineer comp** | $2M – $5M per person annually |

### Investment Trends
- Tech spend rose **~18% in 2025** to sustain latency edges
- Multi-year infrastructure rebuild underway (started 2023, targeting 2025 completion)
- Cloud investment scaling (Google Cloud partnership since 2017)
- FPGA and microwave link investments in the millions
- **Downtime cost**: millions per second of outage

### Revenue Context
- $12.2B revenue (2025) → $6.5B EBITDA → ~53% EBITDA margin
- Technology investment represents ~4-6% of revenue
- Infrastructure spend is a competitive moat, not just a cost center

---

## 5. Pain Points & Challenges

### Current Infrastructure Challenges

1. **Legacy System Complexity**
   - "Messy" codebase with many legacy systems (per Blind reviews)
   - Vast patchwork of technology solutions built over 20+ years
   - Multiple redundant systems across different markets/asset classes
   - Historical focus on quick turnaround over architectural consistency

2. **Operational Complexity**
   - Too many applications and technologies in use
   - Individual systems catering to individual exchanges
   - Different data structures across asset types
   - Complexity in trading practices (systematic vs. high-touch)

3. **Compliance & Regulatory Failures**
   - CAT reporting failure: 42.2 billion inaccurately reported order events
   - Multiple regulatory violations related to coding errors
   - Mismarked trades due to coding errors
   - $1-7M fines per violation (small relative to revenue, but reputational risk)

4. **Technology Rigidity**
   - "Technology stack eventually gets more rigid than you'd like"
   - Difficulty entering new markets/asset classes quickly
   - Need for standardization across global operations

5. **Talent & Retention**
   - Firing entire engineering floors (per Reddit/Blind reports)
   - High-pressure environment (CTO manages systems executing 25-30% of US equity trades)
   - Competition for top quantitative/systems talent

6. **Infrastructure Consolidation**
   - Ongoing multi-year rebuild to consolidate redundancies
   - Need for "one giant binder" — unified, globally scalable infrastructure
   - Target: seamless, integrated system powering operations for 10+ years

### Rebuild Initiative (2023-2025)
- **Goal**: Reduce operational complexity, mitigate redundancies, reduce cost of trading
- **Approach**: Re-architect key systems in a standard, global way
- **Method**: Product managers + COOs embedded in technology organization
- **Progress**: Cloud-native infrastructure overhaul reduced latency by 30%, boosted throughput by 50%
- **Target**: Entirely trading on new system by 2025

---

## 6. Decision Makers & Budget Authority

### Key Technology Leaders

| Name | Title | Role |
|---|---|---|
| **Josh Woods** | Chief Technology Officer | Oversees all technology infrastructure, trading systems, data pipelines, compliance systems |
| **Jeff Maurone** | COO of Technology | Manages product managers, metrics, delivery goals, customer feedback integration |
| **Peng Zhao** | CEO | Overall strategy, market expansion, technology investment approval |
| **Matt Culek** | COO | Operational infrastructure, exchange relationships, day-to-day operations |
| **Kenneth Griffin** | Founder/Chairman | Ultimate authority, ~80% ownership, sets strategic direction |
| **Jim Esposito** | President | Business development, strategic partnerships |
| **David Silber** | (Emerging Technology) | Technology strategy for market operations |

### Budget Authority
- **CTO (Josh Woods)**: Technology infrastructure budget, engineering headcount
- **COO of Technology (Jeff Maurone)**: Technology operations, delivery metrics
- **CEO (Peng Zhao)**: Major technology investments, strategic direction
- **COO (Matt Culek)**: Operational infrastructure, exchange relationships
- **Kenneth Griffin**: Ultimate budget authority, multi-billion dollar decisions

### Hiring Signals
- Active hiring: FPGA Engineers, C++ Engineers, Network Engineers, Market Data Engineers, Quantitative Research Engineers
- Salary range: up to $300K for C++ Software Engineers
- Global footprint: New York, London, Hong Kong, Singapore, Sydney, Tokyo, Miami

---

## 7. Competitive Position

### Market Share
- **US Equities**: ~17% market share, ~40% retail execution
- **Options**: ~30% market share (largest on-exchange options market maker)
- **NYSE**: Largest designated market maker
- **Fixed Income**: Growing presence (rates, credit)
- **Global**: 50+ markets, 150+ venues

### Competitive Advantages
1. **Technology moat**: Proprietary sub-microsecond execution stack
2. **Scale**: $200B+ ADV, 50B+ shares/day peak capacity
3. **Talent**: 1,800+ technologists and quants
4. **Data**: 2PB/day tick data, proprietary analytics
5. **Capital**: $15B+ equity, $50B+ credit access
6. **Network**: Private low-latency network with 50+ colocations

### Competing Firms
- Virtu Financial
- Jane Street
- Optiver
- IMC
- Flow Traders
- Goldman Sachs (trading desk)
- Bank of America (trading desk)

---

## 8. Key Insights for ULL Infrastructure Sales

### What Citadel Values
1. **Deterministic performance** — not average, but tail latency
2. **Reliability under stress** — burst conditions, peak trading
3. **Standardization** — global, consistent architecture
4. **Simplicity** — reducing operational complexity
5. **Time-to-market** — rapid onboarding of new exchanges/asset classes
6. **Total cost of ownership** — not just acquisition cost

### Potential Entry Points
1. **FPGA acceleration** — active hiring, custom solutions
2. **Kernel bypass networking** — DPDK, OpenOnload, RDMA expertise
3. **Low-latency switches** — Arista, cut-through switching
4. **Cloud research platform** — Google Cloud partnership (expanding)
5. **Infrastructure monitoring** — observability for complex distributed systems
6. **Compliance/surveillance** — regulatory technology (pain point)

### What to Emphasize
- Sub-microsecond latency capabilities
- Deterministic performance under burst conditions
- Global deployment and support
- Proven track record with HFT firms
- Total cost of ownership (not just hardware cost)
- Integration with existing C++/FPGA/kernel-bypass stacks

### What to Avoid
- Cloud-first messaging (trading is on-prem)
- Generic "high-performance" claims without specific latency numbers
- Solutions that add complexity rather than reduce it
- Ignoring the compliance/regulatory dimension

---

## 9. Sources

- Citadel Securities careers page and engineering blog
- Bloomberg: "Citadel Securities Nets Record $12 Billion Trading Haul" (2026)
- Business Insider: "Market-Making Giant Citadel Securities is Rebuilding the Tech" (2024)
- eFinancialCareers: "How Citadel Securities is fixing its once 'messy' codebase"
- Google Cloud case study: "How Citadel Securities reimagines quantitative research"
- SEC filings: Citadel Securities LLC financial statements
- The Org: Citadel Securities org chart
- OCC: Josh Woods board profile
- Various industry sources (Traders Magazine, QuantVPS, etc.)

---

*Report prepared for ultra-low-latency-infra project. Data current as of September 2026.*
