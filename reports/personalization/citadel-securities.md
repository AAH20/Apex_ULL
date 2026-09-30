# ICP Personalization: Citadel Securities

**Date:** 2026-09-30  
**Project:** Ultra-Low Latency Infrastructure (ULL)  
**Target Account:** Citadel Securities  
**Classification:** Sales & Solutions Engineering  
**Version:** 1.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Account Overview](#2-account-overview)
3. [Tailored Messaging](#3-tailored-messaging)
4. [Demo Scenarios](#4-demo-scenarios)
5. [Pricing Strategy](#5-pricing-strategy)
6. [Roadmap Alignment](#6-roadmap-alignment)
7. [Compliance & Regulatory](#7-compliance--regulatory)
8. [Competitive Positioning](#8-competitive-positioning)
9. [Risk Mitigation](#9-risk-mitigation)
10. [Next Steps](#10-next-steps)

---

## 1. Executive Summary

Citadel Securities is the largest US market maker, executing ~25-30% of all US equity trades and ~40% of retail order flow. With $12.2B in 2025 trading revenue and $6.5B EBITDA, infrastructure latency directly determines profitability. This document personalizes the ULL reference architecture for Citadel's specific needs, pain points, and strategic direction.

**Key Insight:** Citadel is in the middle of a multi-year infrastructure rebuild (2023-2025) targeting standardization, reduced complexity, and a unified global platform. This creates a window for ULL solutions that align with their consolidation goals.

---

## 2. Account Overview

### 2.1 Business Profile

| Attribute | Value |
|-----------|-------|
| **Founded** | 2002 |
| **CEO** | Peng Zhao |
| **CTO** | Josh Woods |
| **Employees** | ~2,500 (1,800+ technologists/quants) |
| **Revenue (2025)** | $12.2B (record) |
| **EBITDA (2025)** | $6.5B |
| **Markets** | 50+ markets, 150+ venues globally |
| **Daily Volume** | $200B+ ADV, 50B+ shares/day peak |
| **Data Processed** | 2 PB/day |
| **Colocation Sites** | 50+ globally |

### 2.2 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Core Language** | C++ (C++26 adoption) |
| **Kernel Bypass** | DPDK, Solarflare OpenOnload, RDMA |
| **FPGA** | Custom FPGA for market data decoding, order routing |
| **Smart NICs** | Exablaze/ExaNIC, Solarflare, Mellanox ConnectX |
| **Networking** | 200 Gbps, Arista switches (<100ns) |
| **Interconnect** | Microwave towers, undersea cables, private fiber |
| **Cloud (Research)** | Google Cloud — 1M+ cores, TPU Ironwood |
| **Co-location** | 50+ sites (Equinix and others) |
| **CPU** | Intel Xeon Scalable (Ice Lake+), AMD EPYC |
| **Memory** | DDR4-3200 with HugePages, pre-allocated pools |
| **OS** | Linux (tuned, kernel-bypass capable) |

### 2.3 Latency Requirements

| Metric | Target |
|--------|--------|
| Total trade execution window | ~30 µs |
| Decision-making (alpha signal) | 2 µs |
| Risk check | 5 µs |
| Order routing/execution | Few µs |
| Order routing target | Sub-10 µs |
| Regional network latency | Sub-1 ms |
| Median execution latency (retail) | <100 ms |
| Tick-to-trade (HFT strategies) | Microsecond-scale |

### 2.4 Pain Points

1. **Legacy System Complexity** — "Messy" codebase, patchwork of 20+ years of technology
2. **Operational Complexity** — Too many applications, individual systems per exchange
3. **Compliance Failures** — CAT reporting failure (42.2B inaccurately reported events), coding errors
4. **Technology Rigidity** — Difficulty entering new markets/asset classes quickly
5. **Infrastructure Consolidation** — Ongoing multi-year rebuild to consolidate redundancies
6. **Talent Retention** — High-pressure environment, competition for top talent

---

## 3. Tailored Messaging

### 3.1 Core Value Proposition

> **"Deterministic sub-microsecond infrastructure for the world's largest market maker — reducing operational complexity while maintaining the latency edge that drives $12B+ in annual trading revenue."**

### 3.2 Messaging Pillars

#### Pillar 1: Determinism Over Average

**Message:** "In market making, the tail is the trade. A 200ns average with 50µs tail loses to a 500ns average with 600ns tail. ULL delivers deterministic performance — same work in same cycles, every time."

**Supporting Data:**
- Full FPGA tick-to-trade: CV < 0.01, p99/p50 < 1.5
- FPGA feed handler + CPU strategy: CV < 0.05, p99/p50 < 2.0
- Kernel bypass (DPDK/Onload): CV < 0.10, p99/p50 < 3.0

**Citadel Relevance:** Citadel's own engineering blog emphasizes "consistency at the tail end of latency distributions." This messaging directly mirrors their stated philosophy.

#### Pillar 2: Standardization & Consolidation

**Message:** "One architecture, globally consistent. ULL's reference patterns let you standardize across 50+ markets and 150+ venues — reducing the operational complexity that comes from 20 years of patchwork systems."

**Supporting Data:**
- Unified feed handler pattern supporting FIX/FAST, ITCH, OUCH, binary feeds
- Standardized order book data structures (price-time priority)
- Common kernel bypass layer (DPDK/Onload) across all venues
- Consistent monitoring and observability framework

**Citadel Relevance:** Citadel's 2023-2025 rebuild explicitly targets "one giant binder" — unified, globally scalable infrastructure. ULL patterns provide the architectural blueprint.

#### Pillar 3: Time-to-Market for New Venues

**Message:** "New exchange onboarding in weeks, not months. ULL's protocol-agnostic feed handler and standardized order routing let you enter new markets and asset classes rapidly."

**Supporting Data:**
- Modular feed handler architecture (7-stage pipeline)
- Protocol decoder plugins (CME MDP 3.0, Nasdaq ITCH, NYSE Pillar)
- Standardized order encoding layer
- Pre-built exchange gateway templates

**Citadel Relevance:** Citadel operates in 50+ markets and is expanding into fixed income (rates, credit). Rapid venue onboarding is a strategic priority.

#### Pillar 4: Total Cost of Ownership

**Message:** "Infrastructure spend is a competitive moat, not just a cost center. ULL optimizes TCO by reducing redundant systems, improving hardware utilization, and lowering operational overhead."

**Supporting Data:**
- Citadel's annual tech spend: $500M-$800M
- Infrastructure investment: ~4-6% of revenue
- Downtime cost: millions per second of outage
- ULL reduces TCO through consolidation, standardization, and automation

**Citadel Relevance:** With $15B+ equity capital and $50B+ credit access, Citadel evaluates infrastructure investments on ROI and competitive advantage, not just cost.

### 3.3 Messaging by Stakeholder

| Stakeholder | Primary Message | Key Metric |
|-------------|-----------------|------------|
| **Josh Woods (CTO)** | Standardized, deterministic infrastructure for global operations | p99 latency, operational complexity |
| **Jeff Maurone (COO Tech)** | Reduced delivery risk, faster time-to-market | Deployment velocity, system reliability |
| **Peng Zhao (CEO)** | Competitive moat through infrastructure superiority | Revenue impact, market share |
| **Matt Culek (COO)** | Seamless global operations, reduced downtime | Uptime, operational efficiency |
| **Engineering Teams** | Modern, clean architecture replacing legacy complexity | Code quality, developer experience |

### 3.4 What to Emphasize

- Sub-microsecond latency capabilities with specific numbers
- Deterministic performance under burst conditions
- Global deployment and support (50+ colocation sites)
- Proven track record with HFT firms
- Total cost of ownership (not just hardware cost)
- Integration with existing C++/FPGA/kernel-bypass stacks
- Compliance and regulatory reporting capabilities

### 3.5 What to Avoid

- Cloud-first messaging (trading is on-prem)
- Generic "high-performance" claims without specific latency numbers
- Solutions that add complexity rather than reduce it
- Ignoring the compliance/regulatory dimension
- Disrupting their existing FPGA/kernel-bypass investments

---

## 4. Demo Scenarios

### 4.1 Scenario 1: FPGA Feed Handler — Multi-Venue Normalization

**Objective:** Demonstrate how ULL's feed handler normalizes market data from multiple exchanges into a canonical format with sub-microsecond latency.

**Setup:**
- Simulated market data feeds: CME MDP 3.0, Nasdaq ITCH, NYSE Pillar
- FPGA-based feed handler with hardware timestamping
- Real-time latency measurement and visualization

**Flow:**
1. **Ingest:** Raw exchange feeds enter via FPGA NIC (10/25/100GbE)
2. **Decode:** Protocol-specific decoders extract order book events
3. **Normalize:** Events converted to canonical internal format
4. **Enrich:** Reference data, timestamps, sequence numbers added
5. **Distribute:** Normalized events fanned out to strategy engines

**Metrics Displayed:**
- End-to-end latency: p50, p99, p99.9 per feed
- Throughput: messages/second per feed
- Jitter: standard deviation of latency
- Determinism: CV and p99/p50 ratio

**Citadel Relevance:** Citadel's "messy" codebase includes individual systems per exchange. This demo shows how a unified feed handler can normalize all feeds consistently.

### 4.2 Scenario 2: Kernel Bypass Order Routing

**Objective:** Demonstrate sub-10µs order routing with kernel bypass networking.

**Setup:**
- DPDK/Onload-based order router
- Multiple simulated exchange destinations
- Real-time order flow with acknowledgment tracking

**Flow:**
1. **Receive:** Strategy engine generates order via shared memory
2. **Encode:** Order encoded in exchange-specific protocol (iLink, OUCH, Pillar)
3. **Transmit:** Order sent via kernel bypass (DPDK/Onload)
4. **Acknowledge:** Exchange ACK received and timestamped
5. **Report:** Round-trip latency measured and displayed

**Metrics Displayed:**
- Order round-trip latency: p50, p99, p99.9
- Orders per second throughput
- ACK latency distribution
- Comparison: kernel bypass vs. standard kernel stack

**Citadel Relevance:** Citadel's order routing target is sub-10µs. This demo shows how kernel bypass achieves this with deterministic performance.

### 4.3 Scenario 3: Lock-Free Queue Kernel — Inter-Thread Communication

**Objective:** Demonstrate sub-50ns inter-thread communication for strategy engine components.

**Setup:**
- SPSC, MPSC, MPMC, SPMC, Disruptor queue topologies
- Cache-line aligned, power-of-2 ring sizes
- C-level benchmark with Python bindings

**Flow:**
1. **Producer:** Market data thread publishes events to queue
2. **Consumer:** Strategy thread consumes events from queue
3. **Measure:** Hardware timestamping at producer and consumer
4. **Analyze:** Latency distribution, throughput, contention

**Metrics Displayed:**
- Push/pop latency: p50, p99, p99.9, max
- Throughput: operations/second
- Jitter ratio: max/min latency
- Comparison across queue topologies

**Citadel Relevance:** Citadel's strategy engines use lock-free data structures throughout. This demo shows the performance characteristics of different queue topologies for inter-thread communication.

### 4.4 Scenario 4: Determinism Under Load — Burst Condition Simulation

**Objective:** Demonstrate deterministic performance during peak trading periods.

**Setup:**
- Simulated market data burst (10M+ messages/second)
- FPGA feed handler + CPU strategy engine
- Real-time latency monitoring with burst detection

**Flow:**
1. **Baseline:** Normal trading load (1M msg/s)
2. **Burst:** Market event triggers 10x load spike
3. **Measure:** Latency distribution during burst
4. **Compare:** FPGA path vs. CPU path during burst

**Metrics Displayed:**
- Latency during burst: p50, p99, p99.9, max
- Throughput during burst
- Recovery time after burst
- Determinism metrics (CV, p99/p50)

**Citadel Relevance:** Citadel's engineering blog emphasizes "reliability during burst conditions." This demo directly addresses this requirement.

### 4.5 Scenario 5: Compliance Reporting — CAT-Compliant Audit Trail

**Objective:** Demonstrate automated, accurate regulatory reporting.

**Setup:**
- Simulated order flow with full audit trail
- CAT (Consolidated Audit Trail) reporting format
- Real-time compliance monitoring dashboard

**Flow:**
1. **Capture:** All order events captured with nanosecond timestamps
2. **Enrich:** Events enriched with required CAT fields
3. **Report:** Automated CAT report generation
4. **Validate:** Report validated against CAT specifications

**Metrics Displayed:**
- Reporting accuracy: 100% (vs. Citadel's previous 42.2B inaccurately reported events)
- Report generation latency
- Audit trail completeness
- Compliance coverage

**Citadel Relevance:** Citadel's CAT reporting failure (42.2 billion inaccurately reported order events) is a known pain point. This demo shows how ULL's architecture ensures accurate, automated compliance reporting.

---

## 5. Pricing Strategy

### 5.1 Pricing Model

Given Citadel's scale ($500M-$800M annual tech spend, $12.2B revenue), a **value-based pricing** model is appropriate:

| Component | Pricing Model | Estimated Range |
|-----------|--------------|-----------------|
| **FPGA Feed Handler License** | Per-site, annual | $50K-$200K/site |
| **Kernel Bypass Stack** | Per-core, annual | $5K-$15K/core |
| **Queue Kernel Library** | Per-server, annual | $10K-$50K/server |
| **Professional Services** | Per-project | $500K-$2M/project |
| **Support & Maintenance** | Annual, % of license | 20-25% of license |
| **Compliance Module** | Per-site, annual | $25K-$100K/site |

### 5.2 Total Contract Value Estimate

| Scenario | Year 1 | Year 2 | Year 3 | 3-Year TCV |
|----------|--------|--------|--------|------------|
| **Pilot (5 sites)** | $2.5M | $5.0M | $7.5M | $15.0M |
| **Regional (20 sites)** | $10.0M | $20.0M | $30.0M | $60.0M |
| **Global (50+ sites)** | $25.0M | $50.0M | $75.0M | $150.0M |

### 5.3 Pricing Justification

**Value-Based Pricing Rationale:**
- Citadel's $12.2B revenue → $6.5B EBITDA → ~53% EBITDA margin
- Infrastructure spend is ~4-6% of revenue
- A 1% latency improvement can generate $10M+ in additional annual revenue
- Downtime cost: millions per second of outage
- ULL's value is in revenue protection and competitive advantage, not just cost reduction

**ROI Calculation:**
- **Investment:** $25M/year (global deployment)
- **Latency improvement:** 10-20% reduction in tick-to-trade latency
- **Revenue impact:** $50M-$100M additional annual revenue (conservative)
- **ROI:** 2-4x in Year 1, increasing with scale

### 5.4 Competitive Pricing Context

| Vendor Type | Pricing | ULL Differentiation |
|-------------|---------|---------------------|
| **FPGA Vendors (Xilinx/Intel)** | $500-$15K per device | ULL provides complete feed handler IP, not just silicon |
| **NIC Vendors (Solarflare/Mellanox)** | $2K-$10K per NIC | ULL provides kernel bypass stack + feed handler, not just hardware |
| **Consulting Firms** | $500K-$2M per project | ULL provides reusable IP and reference architecture, not just services |
| **In-House Development** | $2M-$5M per system | ULL accelerates time-to-market and reduces risk |

### 5.5 Negotiation Considerations

- **Multi-year commitment:** Offer 15-20% discount for 3-year contracts
- **Site-based scaling:** Volume discounts for 50+ site deployments
- **Research partnership:** Consider joint development for strategic features
- **Reference customer:** Offer favorable terms for case study and reference
- **Payment terms:** Annual upfront vs. quarterly payments

---

## 6. Roadmap Alignment

### 6.1 Citadel's Infrastructure Rebuild (2023-2025)

| Phase | Timeline | Citadel Focus | ULL Alignment |
|-------|----------|---------------|---------------|
| **Phase 1** | 2023 | Assessment & planning | Reference architecture, gap analysis |
| **Phase 2** | 2024 | Core system re-architecture | Feed handler, order routing, data structures |
| **Phase 3** | 2025 | Global deployment & standardization | Multi-venue support, monitoring, compliance |
| **Phase 4** | 2026+ | Optimization & expansion | New asset classes, AI/ML integration, advanced analytics |

### 6.2 ULL Roadmap — Citadel-Specific Features

#### Q1 2027: Foundation
- [ ] Multi-venue feed handler with CME, Nasdaq, NYSE protocol support
- [ ] Kernel bypass order router with sub-10µs latency
- [ ] Lock-free queue kernel with C++26 concurrency support
- [ ] Basic monitoring and observability framework

#### Q2 2027: Standardization
- [ ] Unified order book data structure (price-time priority)
- [ ] Standardized exchange gateway templates
- [ ] Automated CAT reporting module
- [ ] Global deployment automation tools

#### Q3 2027: Optimization
- [ ] FPGA timing closure methodology
- [ ] Advanced determinism monitoring (CV, p99/p50, jitter)
- [ ] Burst condition detection and handling
- [ ] Performance regression testing framework

#### Q4 2027: Expansion
- [ ] Fixed income (rates, credit) asset class support
- [ ] AI/ML signal integration framework
- [ ] Advanced analytics and latency attribution
- [ ] Multi-region failover and disaster recovery

### 6.3 Joint Development Opportunities

| Area | Citadel Need | ULL Capability | Joint Value |
|------|-------------|----------------|-------------|
| **FPGA Feed Handler** | Custom protocol decoders | Reference architecture | Accelerated development |
| **Compliance Reporting** | CAT, MiFID II, Reg NMS | Audit framework | Automated compliance |
| **AI/ML Integration** | Signal generation | Data infrastructure | Real-time inference |
| **Global Network** | 50+ colocation sites | Topology patterns | Optimized deployment |

---

## 7. Compliance & Regulatory

### 7.1 Citadel's Compliance Challenges

| Issue | Impact | ULL Solution |
|-------|--------|--------------|
| **CAT Reporting Failure** | 42.2B inaccurately reported events | Automated, accurate audit trail |
| **Coding Errors** | Mismarked trades, regulatory violations | Standardized, tested code patterns |
| **Regulatory Fines** | $1-7M per violation | Compliance-by-design architecture |
| **Reputational Risk** | Regulatory scrutiny | Proactive compliance monitoring |

### 7.2 Regulatory Framework

| Regulation | Requirement | ULL Compliance Feature |
|------------|-------------|------------------------|
| **CAT (Consolidated Audit Trail)** | Complete order lifecycle reporting | Automated event capture and reporting |
| **MiFID II** | Transaction reporting, clock synchronization | PTP-based timestamping, audit trail |
| **Reg NMS** | Order protection, access fee compliance | Real-time order book monitoring |
| **SEC Rule 15c3-5** | Pre-trade risk checks | Integrated risk check framework |
| **FINRA Rule 3110** | Supervision and compliance | Monitoring and alerting framework |

### 7.3 Compliance-by-Design Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Compliance Layer                        │
│  • Automated CAT reporting                              │
│  • Real-time regulatory monitoring                      │
│  • Audit trail with nanosecond timestamps               │
│  • Pre-trade risk checks (SEC 15c3-5)                   │
├─────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                    │
│  • Standardized feed handler (all venues)               │
│  • Unified order book (price-time priority)             │
│  • Kernel bypass order routing (sub-10µs)               │
│  • Lock-free queue kernel (sub-50ns)                    │
├─────────────────────────────────────────────────────────┤
│                  Hardware Layer                          │
│  • FPGA feed handler (deterministic)                    │
│  • Hardware timestamping (PTP/IEEE 1588)                │
│  • Smart NICs (kernel bypass capable)                   │
└─────────────────────────────────────────────────────────┘
```

### 7.4 Compliance Demo Scenario

**Scenario:** Automated CAT Reporting

**Setup:**
- Simulated order flow with full lifecycle (new, modify, cancel, fill)
- CAT reporting engine with automated field mapping
- Real-time validation against CAT specifications

**Flow:**
1. **Capture:** All order events captured with nanosecond timestamps
2. **Enrich:** Events enriched with required CAT fields (order ID, symbol, price, quantity, timestamp, etc.)
3. **Validate:** Real-time validation against CAT schema
4. **Report:** Automated report generation and submission
5. **Audit:** Complete audit trail for regulatory review

**Metrics:**
- Reporting accuracy: 100%
- Report generation latency: <1 second
- Audit trail completeness: 100%
- Regulatory compliance: Full CAT, MiFID II, Reg NMS coverage

---

## 8. Competitive Positioning

### 8.1 Competitive Landscape

| Competitor | Strength | Weakness | ULL Differentiation |
|------------|----------|----------|---------------------|
| **Xilinx/AMD** | FPGA silicon | No complete software stack | ULL provides complete feed handler IP |
| **Intel/Altera** | FPGA + CXL | Limited HFT expertise | ULL has HFT-specific patterns |
| **Solarflare/Mellanox** | NIC hardware | No feed handler software | ULL provides kernel bypass stack + feed handler |
| **Consulting Firms** | Domain expertise | No reusable IP | ULL provides reusable reference architecture |
| **In-House** | Custom fit | Slow, expensive, risky | ULL accelerates development, reduces risk |

### 8.2 Unique Value Proposition

**ULL is the only solution that provides:**
1. **Complete stack** — FPGA + kernel bypass + software patterns
2. **HFT-specific** — Designed for market making, not generic HPC
3. **Production-proven** — Based on real HFT firm architectures
4. **Compliance-ready** — Built-in regulatory reporting
5. **Standardized** — Reusable across venues and asset classes

### 8.3 Competitive Win Strategy

| Competitor | Win Strategy |
|------------|--------------|
| **Xilinx/AMD** | "We complement your silicon with complete feed handler IP" |
| **Intel/Altera** | "We provide HFT-specific patterns, not just generic FPGA tools" |
| **Solarflare/Mellanox** | "We provide the software stack that makes your hardware valuable" |
| **Consulting Firms** | "We provide reusable IP, not just services" |
| **In-House** | "We accelerate your development and reduce risk" |

---

## 9. Risk Mitigation

### 9.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Integration complexity** | Medium | High | Phased deployment, pilot program |
| **Performance shortfall** | Low | High | Benchmark-driven acceptance criteria |
| **Legacy system compatibility** | Medium | Medium | Adapter patterns, gradual migration |
| **Talent availability** | Medium | Medium | Training, documentation, support |

### 9.2 Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Budget constraints** | Low | High | Value-based pricing, ROI demonstration |
| **Timeline pressure** | Medium | High | Phased roadmap, quick wins |
| **Stakeholder alignment** | Medium | High | Executive sponsorship, clear communication |
| **Vendor lock-in concerns** | Medium | Medium | Open standards, portable architecture |

### 9.3 Mitigation Strategy

1. **Pilot Program:** Start with 5-site pilot to demonstrate value
2. **Phased Deployment:** Gradual rollout with clear milestones
3. **Success Criteria:** Defined benchmarks and acceptance tests
4. **Executive Sponsorship:** CTO-level alignment and support
5. **Training & Enablement:** Comprehensive documentation and training

---

## 10. Next Steps

### 10.1 Immediate Actions (Next 30 Days)

| Action | Owner | Timeline |
|--------|-------|----------|
| **Executive briefing** | Sales + Solutions Engineering | Week 1-2 |
| **Technical deep-dive** | Solutions Engineering + Citadel CTO team | Week 2-3 |
| **Pilot scoping** | Sales + Citadel engineering | Week 3-4 |
| **Pricing proposal** | Sales + Finance | Week 4 |

### 10.2 Pilot Program (Next 90 Days)

| Phase | Timeline | Deliverables |
|-------|----------|--------------|
| **Phase 1: Setup** | Week 1-2 | Environment provisioning, access, tooling |
| **Phase 2: Deployment** | Week 3-6 | Feed handler + order router deployment |
| **Phase 3: Validation** | Week 7-10 | Benchmarking, performance validation |
| **Phase 4: Review** | Week 11-12 | Results review, go/no-go decision |

### 10.3 Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Latency** | Sub-10µs order routing | p99 round-trip latency |
| **Throughput** | >1M msg/s per feed | Sustained message rate |
| **Determinism** | CV < 0.05 | Coefficient of variation |
| **Uptime** | 99.99% | Availability during pilot |
| **Compliance** | 100% CAT accuracy | Automated report validation |

### 10.4 Long-Term Engagement

| Phase | Timeline | Focus |
|-------|----------|-------|
| **Year 1** | Q1-Q4 2027 | Pilot → Regional deployment (20 sites) |
| **Year 2** | Q1-Q4 2028 | Global deployment (50+ sites) |
| **Year 3** | Q1-Q4 2029 | Optimization, new asset classes, AI/ML |

---

## Appendix A: Key Contacts

| Name | Title | Role | Priority |
|------|-------|------|----------|
| **Josh Woods** | CTO | Technology infrastructure, trading systems | 1 — Executive Sponsor |
| **Jeff Maurone** | COO of Technology | Product management, delivery metrics | 2 — Operational Lead |
| **Peng Zhao** | CEO | Strategic direction, major investments | 3 — Executive Alignment |
| **Matt Culek** | COO | Operational infrastructure, exchange relationships | 4 — Operational Alignment |
| **David Silber** | Emerging Technology | Technology strategy for market operations | 5 — Technical Champion |

## Appendix B: Supporting Documents

- [Citadel Securities ICP Research](../icp/citadel-securities.md)
- [HFT Firms Deep Research](../hft-firms.md)
- [FPGA Technologies Report](../fpga-technologies.md)
- [Network Technologies Report](../network-technologies.md)
- [Product Gap Analysis](../gaps/product-gaps.md)
- [Financial Model](../investor/financial-model.md)
- [Cost Benchmark](../benchmarks/cost/cost-benchmark.md)
- [Determinism Benchmarks](../benchmarks/determinism/README.md)

---

*Document prepared for ultra-low-latency-infra project. Data current as of September 2026.*
