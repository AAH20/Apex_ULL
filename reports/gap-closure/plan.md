# Gap Closure Plan — Ultra-Low Latency Infrastructure

**Date:** 2026-09-30  
**Source:** `reports/gaps/product-gaps.md` (87 gaps identified)  
**Scope:** Prioritized execution plan to close all 87 product gaps

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Gap Inventory & Classification](#2-gap-inventory--classification)
3. [Phase 1: Critical Gaps (0–3 months)](#3-phase-1-critical-gaps-03-months)
4. [Phase 2: High Priority (3–6 months)](#4-phase-2-high-priority-36-months)
5. [Phase 3: Medium Priority (6–12 months)](#5-phase-3-medium-priority-612-months)
6. [Phase 4: Lower Priority (12+ months)](#6-phase-4-lower-priority-12-months)
7. [Resource Requirements](#7-resource-requirements)
8. [Success Metrics](#8-success-metrics)
9. [Risk & Dependencies](#9-risk--dependencies)

---

## 1. Executive Summary

The ULL reference architecture has **87 identified gaps** across 10 categories. This plan sequences closure into 4 phases over 18+ months, prioritizing by severity, dependency order, and firm impact.

### Gap Severity Distribution

| Severity | Count | Categories |
|----------|-------|------------|
| Critical | 15 | Firm profiles (4), Pre-trade risk, Compliance, Order book, Exchange connectivity, FPGA feed handler, Market data pipeline |
| High | 22 | Options pricing, Backtesting, Execution algorithms, SOR, Clock sync, Monitoring, AI on FPGA, ML signals, RL, Portfolio mgmt |
| Medium | 28 | Microwave planning, Alternative data, Firm-specific depth, HPC, Research platform, OCaml, Crypto MM |
| Low | 22 | ASIC flow, International expansion, Training tools, Build configs |

### Key Principles

- **Dependency-first:** Exchange connectivity before SOR; order book before matching engine
- **Firm-impact-weighted:** Gaps affecting all 10 firms prioritized over single-firm gaps
- **Build-vs-buy:** Leverage open-source (QuickFIX, kdb+) where possible; build only differentiating components
- **Incremental delivery:** Each phase produces working code, not just documentation

---

## 2. Gap Inventory & Classification

### 2.1 By Category

| Category | Gaps | Critical | High | Medium | Low |
|----------|------|----------|------|--------|-----|
| Firm Coverage | 8 | 4 | 0 | 3 | 1 |
| Infrastructure | 18 | 2 | 3 | 8 | 5 |
| Trading Systems | 28 | 2 | 8 | 12 | 6 |
| Data & Analytics | 20 | 1 | 4 | 9 | 6 |
| Risk & Compliance | 16 | 2 | 2 | 8 | 4 |
| ML/AI | 15 | 0 | 5 | 7 | 3 |
| **Total** | **87** | **15** | **22** | **28** | **22** |

### 2.2 By Firm Impact

| Firms Affected | Gap Count | Priority |
|----------------|-----------|----------|
| All 10 firms | 38 | Highest |
| 5+ firms | 22 | High |
| 2–4 firms | 17 | Medium |
| 1 firm | 10 | Lower |

---

## 3. Phase 1: Critical Gaps (0–3 months)

**Goal:** Establish foundational trading infrastructure and complete firm coverage.

### 3.1 Firm Profiles (4 gaps)

| Gap | Deliverable | Effort | Dependencies |
|-----|-------------|--------|--------------|
| Virtu Financial profile | `reports/firms/virtu.md` | 1 week | Research only |
| Flow Traders profile | `reports/firms/flow-traders.md` | 1 week | Research only |
| Jane Street profile | `reports/firms/jane-street.md` | 1 week | Research only |
| DRW profile | `reports/firms/drw.md` | 1 week | Research only |

**Approach:** Follow existing firm profile format from `reports/hft-firms.md`. Cover: overview, latency infrastructure, technology stack, key differentiators, lessons for ULL architecture.

### 3.2 Exchange Connectivity — FIX Protocol Engine (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| FIX encode/decode | `applications/fix/` — C++ FIX engine | 3 weeks |
| Exchange protocols (iLink, OUCH, Pillar) | Protocol adapter layer | 2 weeks |
| Market data multicast config | Feed configuration module | 1 week |
| Session management | Logon/heartbeat/recovery | 2 weeks |
| Order ID mapping | ID manager | 1 week |
| Gateway failover | Failover logic | 1 week |

**Approach:** Build on QuickFIX open-source library. Create thin C++ wrapper for latency-critical paths. Implement session recovery with sequence number gap fill.

**Architecture:**
```
applications/fix/
├── engine.cpp          # FIX message encode/decode
├── session.cpp         # Logon, heartbeat, recovery
├── order_manager.cpp   # Order ID mapping
├── gateway.cpp         # Multi-exchange gateway
├── failover.cpp        # Hot standby failover
└── exchanges/
    ├── cme_ilink.cpp   # CME iLink 3.0
    ├── nasdaq_ouch.cpp # Nasdaq OUCH 5.0
    └── nyse_pillar.cpp # NYSE Pillar
```

### 3.3 Order Book Implementation (7 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Price-time priority book | `applications/orderbook/` | 3 weeks |
| Full-depth book | Multi-level price ladder | 2 weeks |
| Order modify/cancel | Amendment handling | 1 week |
| Trade reporting/fill generation | Fill engine | 1 week |
| Market data dissemination | Book publisher | 1 week |
| Book snapshot/delta | Snapshot manager | 1 week |
| Multi-asset book | Options/futures support | 2 weeks |

**Approach:** Use existing `applications/data_structures/` (btree, skip_list, hash_map) as foundation. Implement price-time priority using red-black tree per price level with intrusive linked lists for time priority.

**Architecture:**
```
applications/orderbook/
├── book.cpp            # Price-time priority matching
├── price_level.cpp     # Price level management
├── order.cpp           # Order lifecycle
├── fill.cpp            # Trade/fill generation
├── snapshot.cpp         # Book snapshot/delta
└── multi_asset.cpp     # Options/futures support
```

### 3.4 Pre-Trade Risk Framework (8 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Price band check | `applications/risk/` | 1 week |
| Size limit check | Position/size validator | 1 week |
| Position limit check | Real-time position monitor | 1 week |
| Notional exposure check | Exposure calculator | 1 week |
| Fat-finger protection | Anomaly detector | 1 week |
| Duplicate order detection | Order deduplicator | 1 week |
| Kill switch | Emergency stop | 1 week |
| Risk check latency measurement | Latency instrumentation | 1 week |

**Approach:** Implement as FPGA-accelerated pre-trade risk layer (matching production HFT architecture). All checks must complete in <100 ns on FPGA path.

### 3.5 Regulatory Compliance Framework (7 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| CAT reporting | `applications/compliance/cat/` | 3 weeks |
| MiFID II reporting | `applications/compliance/mifid/` | 2 weeks |
| SEC 15c3-5 compliance | Market access rule engine | 2 weeks |
| FINRA 4370 | Business continuity | 1 week |
| Market abuse surveillance | Surveillance module | 2 weeks |
| Order record retention | 7-year storage system | 1 week |
| Regulatory report generation | Report builder | 1 week |

**Approach:** Build compliance reporting pipeline. Use existing `applications/arbitrage/src/models.py` as reference for data models. Integrate with order management system for real-time reporting.

### 3.6 FPGA Feed Handler (7 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Verilog/VHDL feed handler | `applications/fpga/feed_handler/` | 4 weeks |
| Exchange protocol decoders | CME MDP 3.0, Nasdaq ITCH, NYSE Pillar | 3 weeks |
| Bitstream management | Partial reconfiguration | 2 weeks |
| Hardware-in-the-loop test | Test framework | 2 weeks |
| Timing closure methodology | Documentation + scripts | 1 week |
| Power/thermal management | Monitoring code | 1 week |

**Approach:** Start with CME MDP 3.0 decoder (most common). Use existing `docs/patterns/feed-handler.md` as architectural reference. Implement in SystemVerilog with Cocotb testbenches.

### 3.7 Market Data Pipeline (8 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Real-time tick database | `applications/marketdata/` | 3 weeks |
| Tick compression/storage | Compression engine | 2 weeks |
| Historical replay engine | Replay system | 2 weeks |
| Data quality monitoring | Gap/stale detection | 1 week |
| Multi-exchange normalization | Normalizer | 2 weeks |
| Corporate action processing | Corp action handler | 1 week |
| Reference data management | Symbol/contract mapper | 1 week |

**Approach:** Build kdb+-compatible tick store. Use `applications/data_structures/ring_buffer.py` for hot-path buffering. Implement binary compression for historical storage.

---

## 4. Phase 2: High Priority (3–6 months)

**Goal:** Complete trading system capabilities and operational infrastructure.

### 4.1 Options Pricing & Greeks (7 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Black-Scholes/Black model | `applications/pricing/` | 2 weeks |
| Binomial/trinomial tree | Tree pricer | 1 week |
| Monte Carlo pricer | Exotic pricer | 2 weeks |
| Greeks calculation | Delta/gamma/theta/vega/rho | 1 week |
| Volatility surface | Surface constructor | 2 weeks |
| Options market-making | Quote skew/width logic | 2 weeks |
| Dividend/borrow modeling | Cost model | 1 week |

### 4.2 Backtesting Framework (8 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Event-driven backtester | `applications/backtest/` | 3 weeks |
| Market data replay | Realistic latency replay | 2 weeks |
| Transaction cost model | Cost simulator | 1 week |
| Slippage model | Slippage engine | 1 week |
| Capacity/market impact | Impact simulator | 2 weeks |
| Multi-asset backtesting | Cross-asset support | 2 weeks |
| Parameter optimization | Walk-forward/GA | 2 weeks |
| Backtest vs. live comparison | Performance analyzer | 1 week |

### 4.3 Execution Algorithms (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| TWAP/VWAP/POV/IS | `applications/execution/` | 3 weeks |
| Implementation shortfall | IS optimizer | 2 weeks |
| Market impact model | Almgren-Chriss | 2 weeks |
| Execution schedule optimizer | Schedule builder | 2 weeks |
| Real-time execution quality | Quality measurement | 1 week |
| Adaptive execution | Condition-based adjustment | 2 weeks |

### 4.4 Smart Order Router (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Multi-venue routing | `applications/sor/` | 2 weeks |
| Venue latency comparison | Latency monitor | 1 week |
| Order splitting | Splitter algorithm | 2 weeks |
| Venue order type mapping | Type mapper | 1 week |
| Fill/rejection tracking | Rate tracker | 1 week |
| Dynamic venue selection | Queue position-based | 2 weeks |

### 4.5 Clock Synchronization (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| PTP grandmaster config | `applications/ptp/` | 1 week |
| Hardware timestamping | NIC timestamp setup | 1 week |
| Clock drift compensation | Drift algorithm | 2 weeks |
| Boundary/transparent clock | Clock config | 1 week |
| Sync monitoring | Dashboard | 1 week |
| Fallback/holdover | Holdover strategy | 1 week |

### 4.6 Real-Time Monitoring (8 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| P&L dashboard | `applications/monitoring/` | 2 weeks |
| Risk metrics dashboard | VaR/stress test | 2 weeks |
| Trading performance analytics | Performance tracker | 1 week |
| Latency monitoring | Latency dashboard | 1 week |
| Market data quality | Quality dashboard | 1 week |
| Alerting/notification | Alert system | 1 week |
| Trade cost analysis (TCA) | TCA module | 2 weeks |

### 4.7 AI on FPGA (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Quantized NN inference | `applications/fpga/quantized_nn/` | 4 weeks |
| Model compression/pruning | Compression pipeline | 2 weeks |
| Partial reconfig for models | Model update system | 2 weeks |
| Model-to-HDL synthesis | Synthesis tool | 3 weeks |
| FPGA inference benchmarking | Benchmark framework | 1 week |
| FPGA vs. CPU vs. GPU comparison | Comparison framework | 1 week |

### 4.8 ML Signal Pipeline (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Feature engineering | `applications/ml/` | 3 weeks |
| Alpha signal research | Research framework | 2 weeks |
| Signal combination/ensemble | Ensemble methods | 2 weeks |
| Signal decay modeling | Half-life model | 1 week |
| Signal capacity estimation | Capacity estimator | 2 weeks |
| Signal monitoring | Live vs. backtest | 1 week |

### 4.9 Reinforcement Learning (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| RL environment | `applications/rl/` | 3 weeks |
| Policy gradient/Q-learning | RL algorithms | 3 weeks |
| Reward function design | Reward engine | 1 week |
| RL training infrastructure | Training system | 2 weeks |
| RL deployment/inference | Inference engine | 2 weeks |
| RL safety constraints | Safety layer | 1 week |

### 4.10 Portfolio & Position Management (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Real-time position tracking | `applications/portfolio/` | 2 weeks |
| P&L calculation | Mark-to-market | 1 week |
| Exposure monitoring | Net/gross/by asset | 1 week |
| Margin calculation | Margin engine | 2 weeks |
| Position limit enforcement | Limit checker | 1 week |
| End-of-day reconciliation | Reconciliation | 2 weeks |

---

## 5. Phase 3: Medium Priority (6–12 months)

**Goal:** Advanced infrastructure and firm-specific capabilities.

### 5.1 Microwave Network Planning (7 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Link budget calculator | `applications/microwave/` | 2 weeks |
| Tower siting/path planning | Planning tool | 3 weeks |
| Rain fade/weather model | Reliability model | 2 weeks |
| Spectrum licensing guidance | Documentation | 1 week |
| Microwave-vs-fiber decision | Decision framework | 1 week |
| Modem configuration | Config module | 1 week |
| Wireless latency measurement | Measurement methodology | 1 week |

### 5.2 Alternative Data Integration (6 gaps)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| News sentiment | `applications/altdata/` | 3 weeks |
| Social media pipeline | Social feed | 2 weeks |
| Satellite/imagery | Imagery processor | 3 weeks |
| Credit card/transaction | Transaction feed | 2 weeks |
| Options flow/dark pool | Flow analyzer | 2 weeks |
| Alt data signal generation | Signal engine | 2 weeks |

### 5.3 Firm-Specific Depth (15 gaps)

| Firm | Gap | Deliverable | Effort |
|------|-----|-------------|--------|
| Citadel | Microwave topology | Network diagram | 1 week |
| Citadel | Options MM specifics | MM module | 2 weeks |
| Jump | AI/ML architecture | Architecture doc | 1 week |
| Jump | HPC cluster specs | Cluster design | 2 weeks |
| HRT | Custom kernel mods | Kernel patch docs | 2 weeks |
| HRT | corral/wavetools | Integration guide | 1 week |
| Tower | HAIL foundation model | Model architecture | 2 weeks |
| Tower | Rust infrastructure | Rust code | 3 weeks |
| Optiver | Compile-time Greeks | Template metaprogramming | 2 weeks |
| Optiver | 80-in-8 training | Training tool | 1 week |
| IMC | Java-C++ bridge | Bridge architecture | 2 weeks |
| IMC | 5x HPC expansion | Expansion plan | 1 week |
| IMC | ASIC design | ASIC flow | 4 weeks |
| IMC | Self-optimizing liquidity | RL/optimization | 3 weeks |

---

## 6. Phase 4: Lower Priority (12+ months)

**Goal:** Long-term strategic capabilities.

### 6.1 ASIC Design Flow (1 gap)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Full ASIC tapeout | `applications/asic/` | 6 months |

### 6.2 HPC Cluster Architecture (1 gap)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| GPU cluster deployment | `applications/hpc/` | 3 months |

### 6.3 Research Platform / DSL (1 gap)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Language + compiler | `applications/research/` | 4 months |

### 6.4 OCaml Integration (1 gap)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| OCaml FFI + trading | `applications/ocaml/` | 2 months |

### 6.5 Crypto Market Making (1 gap)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Crypto-specific stack | `applications/crypto/` | 3 months |

### 6.6 International Expansion (1 gap)

| Gap | Deliverable | Effort |
|-----|-------------|--------|
| Multi-region deployment | Deployment framework | 2 months |

---

## 7. Resource Requirements

### 7.1 Team Composition

| Role | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|
| C++ Engineers | 3 | 4 | 3 | 2 |
| FPGA Engineers | 2 | 2 | 1 | 1 |
| Python Engineers | 2 | 3 | 2 | 1 |
| ML Engineers | 0 | 3 | 2 | 1 |
| DevOps/SRE | 1 | 2 | 1 | 1 |
| Researchers | 1 | 1 | 2 | 1 |
| **Total** | **9** | **15** | **11** | **7** |

### 7.2 Infrastructure

| Resource | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|----------|---------|---------|---------|---------|
| FPGA dev boards | 2 | 4 | 2 | 1 |
| GPU cluster | 0 | 1 | 1 | 1 |
| Colo space | 1 | 2 | 2 | 2 |
| Exchange sim | 1 | 2 | 2 | 2 |

### 7.3 Estimated Cost

| Phase | Duration | Team Cost | Infrastructure | Total |
|-------|----------|-----------|---------------|-------|
| Phase 1 | 3 months | $675K | $150K | $825K |
| Phase 2 | 3 months | $1.1M | $300K | $1.4M |
| Phase 3 | 6 months | $1.6M | $400K | $2.0M |
| Phase 4 | 6 months | $1.0M | $300K | $1.3M |
| **Total** | **18 months** | **$4.4M** | **$1.2M** | **$5.6M** |

---

## 8. Success Metrics

### 8.1 Phase 1 Targets

| Metric | Target |
|--------|--------|
| Firm profiles complete | 4/4 |
| FIX engine throughput | >100K msg/sec |
| Order book latency | <500 ns (FPGA), <2 μs (CPU) |
| Risk check latency | <100 ns |
| Compliance reports | CAT + MiFID II |
| FPGA feed handler | CME MDP 3.0 working |
| Tick database | >1M ticks/sec ingestion |

### 8.2 Phase 2 Targets

| Metric | Target |
|--------|--------|
| Options pricer | <1 μs per Greeks calculation |
| Backtester | 1-year tick data in <1 hour |
| Execution algorithms | TWAP/VWAP/POV/IS |
| SOR | <5 μs routing decision |
| Clock sync | <100 ns offset |
| Monitoring | <1 sec alert latency |
| AI on FPGA | <1 μs inference |
| ML signals | 5+ live signals |
| RL | Working trading agent |
| Portfolio | Real-time P&L |

### 8.3 Overall Targets

| Metric | Target |
|--------|--------|
| Total gaps closed | 87/87 |
| Code coverage | >80% |
| Test pass rate | >95% |
| Documentation | 100% API docs |
| Benchmarks | All benchmarks passing |

---

## 9. Risk & Dependencies

### 9.1 Critical Dependencies

```
Firm Profiles (no deps)
    ↓
Exchange Connectivity → Order Book → Matching Engine
    ↓                        ↓
Pre-Trade Risk ←──────────────┘
    ↓
Regulatory Compliance
    ↓
Market Data Pipeline → Backtesting → Strategy Engine
    ↓
FPGA Feed Handler → AI on FPGA
    ↓
Monitoring → Execution Algorithms → SOR
```

### 9.2 Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FPGA talent shortage | High | High | Start hiring in Phase 1; use contractors |
| Exchange protocol changes | Medium | High | Build protocol adapter layer for flexibility |
| Scope creep | High | Medium | Strict phase gates; MVP first |
| Performance targets missed | Medium | High | Benchmark early; iterate |
| Regulatory changes | Low | High | Modular compliance design |
| Key person dependency | Medium | High | Documentation + pair programming |

### 9.3 Phase Gate Criteria

| Phase | Gate Criteria |
|-------|---------------|
| Phase 1 → 2 | All critical gaps closed; FIX engine + order book + risk + compliance working |
| Phase 2 → 3 | All high-priority gaps closed; backtesting + execution + monitoring operational |
| Phase 3 → 4 | All medium-priority gaps closed; microwave + alt data + firm-specific complete |
| Phase 4 → Done | All 87 gaps closed; all benchmarks passing; documentation complete |

---

*Plan created: 2026-09-30*  
*Project: ultra-low-latency-infra*  
*Total gaps: 87*  
*Estimated completion: 18+ months*  
*Estimated cost: $5.6M*
