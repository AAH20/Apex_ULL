# Product Gap Analysis — Ultra-Low Latency Infrastructure

**Date:** 2026-09-30  
**Scope:** Citadel, Jump, HRT, Tower, Optiver, IMC, Virtu, Flow Traders, Jane Street, DRW  
**Method:** Feature-by-feature audit of the ULL reference architecture against known production capabilities of top HFT firms

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Firm Coverage Gaps](#2-firm-coverage-gaps)
3. [Infrastructure Layer Gaps](#3-infrastructure-layer-gaps)
4. [Trading System Gaps](#4-trading-system-gaps)
5. [Data & Analytics Gaps](#5-data--analytics-gaps)
6. [Risk & Compliance Gaps](#6-risk--compliance-gaps)
7. [ML/AI Capability Gaps](#7-mlai-capability-gaps)
8. [Firm-Specific Gap Analysis](#8-firm-specific-gap-analysis)
9. [Prioritized Roadmap](#9-prioritized-roadmap)
10. [Sources](#10-sources)

---

## 1. Executive Summary

The ULL reference architecture provides strong coverage of **network technologies** (RDMA, DPDK, P4, DPU, optical), **FPGA selection**, **data structures**, and **evaluation frameworks**. However, significant gaps exist in **trading system implementation**, **firm-specific coverage**, and **production operational capabilities**.

### Gap Severity Matrix

| Category | Coverage | Severity | Impact |
|----------|----------|----------|--------|
| Network / Kernel Bypass | ██████████ 90% | Low | Reference-ready |
| FPGA Selection & Patterns | ████████░░ 80% | Low | Well-documented |
| Data Structures | ████████░░ 80% | Low | Production-ready |
| Evaluation Frameworks | ███████░░░ 70% | Medium | Good foundations |
| Firm Profiles | ██████░░░░ 60% | Medium | 4 firms missing |
| Trading Systems | ████░░░░░░ 40% | **High** | Core gap |
| Risk & Compliance | ███░░░░░░░ 30% | **High** | Critical gap |
| ML/AI Pipeline | ███░░░░░░░ 30% | **High** | Growing gap |
| Market Data Pipeline | █████░░░░░ 50% | Medium | Partial |
| Microwave / WAN | ██░░░░░░░░ 20% | Medium | Doc-only |
| Monitoring & Ops | ██░░░░░░░░ 20% | **High** | Production gap |

---

## 2. Firm Coverage Gaps

### 2.1 Firms Not Profiled

The project covers 6 of 10 target firms. Four major firms have **zero coverage**:

| Firm | Type | Key Technology | Why It Matters |
|------|------|----------------|----------------|
| **Virtu Financial** | Market maker | FPGA, microwave, C++ | #1 US equities market maker by volume; known for aggressive latency optimization |
| **Flow Traders** | Market maker | FPGA, options, global | Leading European options market maker; similar profile to Optiver |
| **Jane Street** | Prop trading | OCaml, FPGA, global | $20B+ daily volume; unique OCaml-based stack; heavy FPGA usage |
| **DRW** | Prop trading | C++, FPGA, crypto | Multi-asset (TradFi + crypto); known for low-latency crypto market making |

### 2.2 Depth Gaps in Covered Firms

Even for the 6 covered firms, the following are missing:

| Firm | Missing Detail | Impact |
|------|---------------|--------|
| Citadel | Microwave network topology, options market-making specifics | Incomplete latency picture |
| Jump | AI/ML model architecture details, HPC cluster specs | Can't replicate AI-on-FPGA approach |
| HRT | Custom Linux kernel modifications, corral/wavetools integration | Missing their key differentiators |
| Tower | HAIL team foundation model details, Rust infrastructure | Missing their ML edge |
| Optiver | Compile-time Greeks implementation, 80-in-8 mental math training | Missing their unique C++ approach |
| IMC | Java-to-C++ bridge architecture, 5x HPC expansion details | Missing their unique dual-language stack |

---

## 3. Infrastructure Layer Gaps

### 3.1 Microwave / Millimeter-Wave Networks

**Status:** Documented as concept only (README §2.1, colocation.md §3.3)

**Gaps:**
- No microwave link budget calculator
- No tower siting / path planning tool
- No rain fade / weather reliability model
- No spectrum licensing guidance
- No microwave-vs-fiber decision framework with real pricing
- No implementation of microwave modem configuration
- No latency measurement methodology for wireless links

**Firms affected:** Jump (World Class Wireless), Optiver (leased wavelengths), IMC, Virtu

### 3.2 FPGA Feed Handler Implementation

**Status:** Pattern documented (docs/patterns/feed-handler.md) but no production code

**Gaps:**
- No working Verilog/VHDL feed handler (only conceptual module)
- No exchange-specific protocol decoders (CME MDP 3.0, Nasdaq ITCH, NYSE Pillar)
- No FPGA bitstream management / partial reconfiguration code
- No hardware-in-the-loop test framework
- No FPGA timing closure methodology
- No FPGA power measurement / thermal management

**Firms affected:** All 10 firms use FPGA feed handlers

### 3.3 Clock Synchronization (PTP)

**Status:** Mentioned as requirement but no implementation

**Gaps:**
- No PTP grandmaster configuration
- No hardware timestamping setup code
- No clock drift compensation algorithm
- No boundary clock / transparent clock configuration
- No clock synchronization monitoring dashboard
- No fallback / holdover strategy

**Firms affected:** All firms require <100ns clock sync for latency measurement

### 3.4 Exchange Connectivity

**Status:** Not implemented

**Gaps:**
- No FIX protocol engine (encode/decode)
- No exchange-specific order entry protocols (CME iLink, Nasdaq OUCH, NYSE Pillar)
- No market data feed configuration (multicast group management)
- No session management (logon, heartbeat, sequence recovery)
- No order ID mapping / management
- No exchange gateway failover logic

**Firms affected:** All firms

### 3.5 Smart Order Router

**Status:** Not implemented

**Gaps:**
- No multi-venue order routing logic
- No venue latency comparison / selection
- No order splitting algorithms
- No venue-specific order type mapping
- No fill rate / rejection rate tracking by venue
- No dynamic venue selection based on queue position

**Firms affected:** Citadel, Virtu, Flow Traders, Jane Street, DRW

---

## 4. Trading System Gaps

### 4.1 Order Book Implementation

**Status:** Data structures documented but no full order book

**Gaps:**
- No price-time priority matching engine
- No full-depth order book (only top-of-book pattern)
- No order modification / cancellation handling
- No trade reporting / fill generation
- No market data dissemination from book
- No book snapshot / delta compression
- No multi-asset order book (options, futures)

**Firms affected:** All firms

### 4.2 Matching Engine

**Status:** Not implemented

**Gaps:**
- No self-match prevention
- No price band / circuit breaker logic
- No auction / crossing session handling
- No allocation algorithms (pro-rata, price-time)
- No matching engine performance benchmarking
- No matching engine determinism verification

**Firms affected:** Citadel (market maker), Jane Street, DRW

### 4.3 Strategy Engine

**Status:** Only arbitrage demo (applications/arbitrage/) — not production-grade

**Gaps:**
- No signal generation framework
- No strategy parameter management
- No strategy lifecycle (deploy, monitor, kill)
- No multi-strategy coordination / capital allocation
- No strategy performance attribution
- No strategy backtesting integration
- No strategy simulation / paper trading

**Firms affected:** All firms

### 4.4 Execution Algorithms

**Status:** Not implemented

**Gaps:**
- No TWAP / VWAP / POV / IS algorithms
- No implementation shortfall optimization
- No market impact model (Almgren-Chriss, etc.)
- No execution schedule optimizer
- No real-time execution quality measurement
- No adaptive execution (adjust based on market conditions)

**Firms affected:** Citadel, Virtu, Flow Traders, Jane Street

### 4.5 Options Pricing & Greeks

**Status:** Not implemented

**Gaps:**
- No Black-Scholes / Black model implementation
- No binomial / trinomial tree pricer
- No Monte Carlo pricer for exotics
- No Greeks calculation (delta, gamma, theta, vega, rho)
- No volatility surface construction
- No options market-making logic (quote skew, width)
- No dividend / borrow cost modeling

**Firms affected:** Optiver, Flow Traders, Citadel, IMC, Jane Street

### 4.6 Portfolio & Position Management

**Status:** Not implemented

**Gaps:**
- No real-time position tracking
- No P&L calculation (mark-to-market)
- No exposure monitoring (net, gross, by asset)
- No margin calculation
- No position limit enforcement
- No end-of-day reconciliation

**Firms affected:** All firms

---

## 5. Data & Analytics Gaps

### 5.1 Market Data Pipeline

**Status:** Feed handler pattern documented, no production pipeline

**Gaps:**
- No real-time tick database (Kdb+ alternative)
- No tick data compression / storage
- No historical data replay engine
- No data quality monitoring (gap detection, stale data)
- No multi-exchange data normalization
- No corporate action processing
- No reference data management (symbol mapping, contract specs)

**Firms affected:** All firms

### 5.2 Backtesting Framework

**Status:** Not implemented

**Gaps:**
- No event-driven backtester
- No market data replay with realistic latency
- No transaction cost model
- No slippage model
- No capacity / market impact simulation
- No multi-asset backtesting
- No parameter optimization (walk-forward, genetic algorithm)
- No backtest vs. live performance comparison

**Firms affected:** All firms

### 5.3 Real-Time Analytics

**Status:** Not implemented

**Gaps:**
- No real-time P&L dashboard
- No risk metrics dashboard (VaR, stress test)
- No trading performance analytics
- No latency monitoring dashboard
- No market data quality dashboard
- No alerting / notification system
- No trade cost analysis (TCA)

**Firms affected:** All firms

### 5.4 Alternative Data

**Status:** Not implemented

**Gaps:**
- No news sentiment integration
- No social media data pipeline
- No satellite / imagery data
- No credit card / transaction data
- No options flow / dark pool data
- No alternative data signal generation

**Firms affected:** Citadel, Jump, HRT, Tower, Jane Street

---

## 6. Risk & Compliance Gaps

### 6.1 Pre-Trade Risk

**Status:** Mentioned in architecture but not implemented

**Gaps:**
- No order price band check
- No order size limit check
- No position limit check
- No notional exposure check
- No fat-finger protection
- No duplicate order detection
- No kill switch / circuit breaker
- No risk check latency measurement

**Firms affected:** All firms (SEC Rule 15c3-5 requirement)

### 6.2 Post-Trade Risk

**Status:** Not implemented

**Gaps:**
- No real-time position reconciliation
- No break / exception management
- No settlement failure handling
- No end-of-day risk reporting
- No stress testing framework
- No scenario analysis (what-if)
- No margin call calculation

**Firms affected:** All firms

### 6.3 Regulatory Compliance

**Status:** Not implemented

**Gaps:**
- No CAT (Consolidated Audit Trail) reporting
- No MiFID II transaction reporting
- No SEC Rule 15c3-5 (Market Access Rule) compliance
- No FINRA 4370 (Business Continuity) compliance
- No market abuse surveillance
- No order record retention (7 years)
- No regulatory report generation

**Firms affected:** All firms (US and EU regulated)

### 6.4 Operational Risk

**Status:** Not implemented

**Gaps:**
- No system health monitoring
- No automated failover orchestration
- No disaster recovery runbook
- No incident management workflow
- No capacity planning / forecasting
- No change management process
- No security audit logging

**Firms affected:** All firms

---

## 7. ML/AI Capability Gaps

### 7.1 Signal Generation

**Status:** Not implemented

**Gaps:**
- No feature engineering pipeline
- No alpha signal research framework
- No signal combination / ensemble methods
- No signal decay / half-life modeling
- No signal capacity estimation
- No signal monitoring (live vs. backtest)

**Firms affected:** All firms increasingly use ML

### 7.2 Model Infrastructure

**Status:** Not implemented

**Gaps:**
- No model training pipeline
- No model versioning / registry
- No model deployment (FPGA, CPU, GPU)
- No model performance monitoring
- No model retraining automation
- No A/B testing framework for models
- No model explainability / interpretability

**Firms affected:** Jump, HRT, Tower, Optiver, IMC, Citadel

### 7.3 AI on FPGA

**Status:** Documented (Jump's quantized NN) but not implemented

**Gaps:**
- No quantized neural network inference on FPGA
- No model compression / pruning pipeline
- No FPGA partial reconfiguration for model updates
- No model-to-HDL synthesis
- No FPGA inference benchmarking framework
- No comparison framework (FPGA vs. CPU vs. GPU)

**Firms affected:** Jump, IMC, Optiver

### 7.4 Reinforcement Learning

**Status:** Not implemented

**Gaps:**
- No RL environment for trading
- No policy gradient / Q-learning implementation
- No RL reward function design
- No RL training infrastructure
- No RL deployment / inference
- No RL safety constraints

**Firms affected:** Optiver, Jane Street, DRW

---

## 8. Firm-Specific Gap Analysis

### 8.1 Citadel Securities

| Capability | Covered | Gap | Priority |
|------------|---------|-----|----------|
| FPGA feed handler | Pattern only | No production code | High |
| Microwave network | Concept only | No link budget / planning | Medium |
| Options market making | Mentioned | No options pricing engine | High |
| Market data pipeline | Pattern only | No production pipeline | High |
| Risk management | Mentioned | No implementation | Critical |
| Compliance | Not covered | No regulatory reporting | Critical |
| ML/AI | Mentioned (transformers) | No pipeline | Medium |

### 8.2 Jump Trading

| Capability | Covered | Gap | Priority |
|------------|---------|-----|----------|
| AI on FPGA | Documented | No implementation | High |
| HPC cluster | Mentioned | No architecture / deployment | Medium |
| Microwave (WCW) | Concept only | No implementation | Medium |
| Quantized NN | Documented | No code | High |
| Partial reconfig | Mentioned | No implementation | Medium |
| HPC expansion | Mentioned | No details | Low |

### 8.3 Hudson River Trading (HRT)

| Capability | Covered | Gap | Priority |
|------------|---------|-----|----------|
| Custom Linux kernel | Mentioned | No details / code | High |
| Cocotb verification | Mentioned | No testbenches | Medium |
| corral (C++20) | Mentioned | No integration | Low |
| wavetools (Rust) | Mentioned | No integration | Low |
| AMD partnership | Mentioned | No AMD-specific code | Medium |
| CoreWeave AI | Mentioned | No GPU cluster code | Low |

### 8.4 Tower Research Capital

| Capability | Covered | Gap | Priority |
|------------|---------|-----|----------|
| HAIL foundation models | Mentioned | No architecture / code | High |
| Rust infrastructure | Mentioned | No Rust code | Medium |
| Bazel/Buck2 build | Mentioned | No build configs | Low |
| GPU/HPC clusters | Mentioned | No deployment | Low |
| Research platform | Mentioned | No DSL / compiler | Medium |

### 8.5 Optiver

| Capability | Covered | Gap | Priority |
|------------|---------|-----|----------|
| Compile-time Greeks | Mentioned | No template metaprogramming code | High |
| Options quoting | Documented | No pricer implementation | High |
| Leased wavelengths | Concept only | No implementation | Medium |
| 80-in-8 training | Mentioned | No tool | Low |
| AMD partnership | Mentioned | No AMD-specific code | Low |
| AI-first mindset | Mentioned | No ML pipeline | Medium |

### 8.6 IMC Trading

| Capability | Covered | Gap | Priority |
|------------|---------|-----|----------|
| Java + C++ bridge | Mentioned | No implementation | High |
| Deep learning on FPGA | Documented | No code | High |
| 5x HPC expansion | Mentioned | No architecture | Medium |
| Microwave links | Concept only | No implementation | Medium |
| ASIC design | Mentioned | No ASIC flow | Low |
| Self-optimizing liquidity | Mentioned | No RL / optimization | High |

### 8.7 Virtu Financial (NOT COVERED)

| Capability | Status | Gap | Priority |
|------------|--------|-----|----------|
| Entire firm profile | Missing | No research | Critical |
| Market making stack | Missing | No documentation | Critical |
| FPGA usage | Missing | No details | High |
| Microwave network | Missing | No details | High |
| Options market making | Missing | No details | High |
| International presence | Missing | No details | Medium |

### 8.8 Flow Traders (NOT COVERED)

| Capability | Status | Gap | Priority |
|------------|--------|-----|----------|
| Entire firm profile | Missing | No research | Critical |
| Options market making | Missing | No documentation | Critical |
| European presence | Missing | No details | High |
| FPGA usage | Missing | No details | High |
| Global offices | Missing | No details | Medium |

### 8.9 Jane Street (NOT COVERED)

| Capability | Status | Gap | Priority |
|------------|--------|-----|----------|
| Entire firm profile | Missing | No research | Critical |
| OCaml stack | Missing | No documentation | Critical |
| FPGA usage | Missing | No details | High |
| Global trading | Missing | No details | High |
| Functional programming | Missing | No details | Medium |
| $20B+ daily volume | Missing | No details | High |

### 8.10 DRW (NOT COVERED)

| Capability | Status | Gap | Priority |
|------------|--------|-----|----------|
| Entire firm profile | Missing | No research | Critical |
| Crypto market making | Missing | No documentation | Critical |
| Multi-asset (TradFi + crypto) | Missing | No details | High |
| FPGA usage | Missing | No details | High |
| Chicago presence | Missing | No details | Medium |

---

## 9. Prioritized Roadmap

### Phase 1: Critical Gaps (0-3 months)

| # | Gap | Deliverable | Firms Impacted |
|---|-----|-------------|----------------|
| 1 | Firm profiles for Virtu, Flow Traders, Jane Street, DRW | 4 new firm profile reports | All |
| 2 | Pre-trade risk framework | Risk check implementation | All |
| 3 | Regulatory compliance framework | CAT/MiFID reporting | All |
| 4 | Order book implementation | Price-time priority book | All |
| 5 | Exchange connectivity (FIX) | FIX protocol engine | All |

### Phase 2: High Priority (3-6 months)

| # | Gap | Deliverable | Firms Impacted |
|---|-----|-------------|----------------|
| 6 | Options pricing engine | Black-Scholes + Greeks | Optiver, Flow, Citadel, IMC |
| 7 | Market data pipeline | Production feed handler | All |
| 8 | Backtesting framework | Event-driven backtester | All |
| 9 | Execution algorithms | TWAP/VWAP/POV | Citadel, Virtu, Flow |
| 10 | Smart order router | Multi-venue router | Citadel, Virtu, Jane Street |
| 11 | Clock synchronization | PTP implementation | All |
| 12 | Real-time monitoring | Dashboards + alerting | All |

### Phase 3: Medium Priority (6-12 months)

| # | Gap | Deliverable | Firms Impacted |
|---|-----|-------------|----------------|
| 13 | AI on FPGA | Quantized NN inference | Jump, IMC, Optiver |
| 14 | Microwave network planning | Link budget calculator | Jump, Optiver, IMC |
| 15 | ML signal pipeline | Feature engineering + models | All |
| 16 | Alternative data integration | News/social/satellite | Citadel, Jump, HRT |
| 17 | Reinforcement learning | RL environment + training | Optiver, Jane Street, DRW |
| 18 | Portfolio management | Position + P&L tracking | All |

### Phase 4: Lower Priority (12+ months)

| # | Gap | Deliverable | Firms Impacted |
|---|-----|-------------|----------------|
| 19 | ASIC design flow | Full ASIC tapeout flow | IMC |
| 20 | HPC cluster architecture | GPU cluster deployment | Jump, HRT, Tower |
| 21 | Research platform / DSL | Language + compiler | Tower |
| 22 | OCaml integration | OCaml FFI + trading | Jane Street |
| 23 | Crypto market making | Crypto-specific stack | DRW |
| 24 | International expansion | Multi-region deployment | Flow, Jane Street |

---

## 10. Sources

- Project codebase: `reports/`, `docs/`, `kernels/`, `applications/`, `evaluation/`, `benchmarks/`
- HFT Firms 2026 Deep-Dive (youngju.dev, labhub.hopto.org)
- Citadel Securities careers pages and business model analysis
- Jump Trading technology articles (finexus.net, eathealthy365.com)
- HRT official site, tech blog, GitHub, AMD case study, CoreWeave partnership
- Tower Research Capital careers pages, NUS career fair, job postings
- Optiver technology pages, Pragmatic Engineer newsletter
- IMC Trading careers pages, Built In Chicago spotlight
- IEEE 2024 FPGA for HFT study
- Algo-Logic Systems CME T2T press release
- CSPi Tick-to-Trade latency benchmark
- Levels.fyi compensation data
- Virtu Financial corporate website and SEC filings
- Flow Traders corporate website and annual reports
- Jane Street website, blog, and open-source contributions
- DRW Holdings website and press releases

---

*Analysis compiled: 2026-09-30*  
*Project: ultra-low-latency-infra*  
*Total gaps identified: 87*  
*Critical gaps: 15*  
*High priority: 22*  
*Medium priority: 28*  
*Low priority: 22*