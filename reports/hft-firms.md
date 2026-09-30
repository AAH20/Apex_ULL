# Ultra-Low Latency HFT Firms: Deep Research Report

**Date:** September 2026  
**Scope:** Citadel Securities, Jump Trading, Hudson River Trading (HRT), Tower Research Capital, Optiver, IMC Trading

---

## Table of Contents

1. [Industry Context: The Latency Landscape](#1-industry-context-the-latency-landscape)
2. [Citadel Securities](#2-citadel-securities)
3. [Jump Trading](#3-jump-trading)
4. [Hudson River Trading (HRT)](#4-hudson-river-trading-hrt)
5. [Tower Research Capital](#5-tower-research-capital)
6. [Optiver](#6-optiver)
7. [IMC Trading](#7-imc-trading)
8. [Cross-Firm Comparison](#8-cross-firm-comparison)
9. [Key Technology Patterns](#9-key-technology-patterns)
10. [Sources](#10-sources)

---

## 1. Industry Context: The Latency Landscape

### The Physics of Speed

In 2026, the fundamental physics driving HFT infrastructure remains unchanged:

| Medium | Chicago ↔ New York Latency | Speed of Light Factor |
|--------|---------------------------|----------------------|
| Fiber optic | ~7.2 ms | ~67% of c (index of refraction) |
| Microwave wireless | ~4.7 ms | ~99% of c (through air) |
| **Advantage** | **~2.5 ms saved** | **~50% faster than fiber** |

A single microwave route can lease for **>$10M/year**. The key operators building these networks include Jump Trading's subsidiary **World Class Wireless**, **McKay Brothers**, and **New Line Networks**.

### Exchange Matching Engine Latencies (2026)

| Exchange | Matching Latency | Gateway Round-Trip |
|----------|-----------------|-------------------|
| CME Globex | ~10 μs | <100 μs |
| NYSE Pillar | ~10 μs | <100 μs |
| Nasdaq INET | ~10 μs | <100 μs |

### Tick-to-Trade Latency Hierarchy

| Implementation | Typical Latency | Jitter | Use Case |
|---------------|----------------|--------|----------|
| Standard kernel network stack | 10–50 μs | High | Research, non-latency-bound |
| Kernel bypass (Onload, DPDK) | 1–5 μs | Moderate | Most latency-sensitive strategies |
| Hybrid: FPGA feed handler + CPU strategy | 100s of ns – ~1 μs | Low on fast path | Fast hardware trigger, complex decision in software |
| Full FPGA tick-to-trade | 150–500 ns | Very low, deterministic | Simple, well-defined hot path |
| Fastest published wire-to-wire | <25 ns | Ultra-low | Research benchmarks |

### FPGA Latency Benchmarks (Published)

- **IEEE 2024 study**: FPGA-based system achieved **480 ns average latency**, processing up to **150,000 orders/second**
- **Algo-Logic Systems (CME T2T)**: Sub-microsecond wire-to-wire; PHY+MAC round-trip of **89.6 ns**
- **CSPi ARC E-Class adapter**: Mean tick-to-trade of **1.538 μs** (FPGA-based NIC)
- **Optiver's options quoting engine**: Reacts to new quote in **<500 ns**
- **HRT's matching-engine simulator**: Data structures aligned at **<10 ns granularity**

---

## 2. Citadel Securities

### Overview

| Attribute | Detail |
|-----------|--------|
| Founded | 2002 (Chicago) |
| Founder | Ken Griffin |
| Revenue (2024) | ~$23B |
| Operating Income (2024) | >$10B |
| Employees | ~2,500+ (≈1,000 quants/engineers) |
| Market Share | ~25% US equity volume, ~30% US options, >40% US retail order flow |
| Infrastructure Spend | ~$500M–$800M annually |
| R&D/Hardware Spend | ~$200–300M (2025) |
| Co-location Sites | 50+ globally (Equinix partnership) |
| Daily Data | 2 PB |
| Daily Notional | $50B+ |
| Uptime | 99.99% |

### Latency Infrastructure

- **Sub-100 ms median execution latency** (2025 reported)
- **Sub-10 μs order routing** target
- **Sub-1 ms regional latency** across private network
- **50+ co-location sites** with Equinix globally
- **Private fiber + microwave network** linking Chicago, New York, London, Hong Kong
- **FPGA gateways** for kernel-bypass packet processing
- **Cross-asset hedging**: Makes markets in SPY, S&P 500 futures, and all 500 constituents simultaneously

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Core Trading | C++ (ultra-low latency, template-heavy) |
| Research/Analysis | Python, R |
| Hardware | FPGA (Solarflare/Xilinx Onload + ef_vi; Mellanox/NVIDIA Connect-X + DPDK) |
| Network | Microwave + ULL fiber, private WAN |
| Data | Kdb+, petabyte-scale tick databases |
| ML/AI | Transformer-based signal models (since 2024–2025) |

### Known Benchmarks

- Sub-100 ms median execution latency (2025)
- Sub-10 μs order routing
- >10 billion daily quotes
- >50 billion shares/day peak capacity
- $200B+ ADV

### Hiring Profiles

**Quantitative Developer/Research Engineer:**
- Degree in CS, Mathematics, Statistics, or equivalent
- Expert-level C++ with high-performance, low-latency code history
- Understanding of modern CPU architectures (pipelines, caches, memory models)
- Strong mathematical and quantitative foundation
- Experience with distributed computing, ML, NLP, platform development preferred

**Interview Process:**
1. Recruiter conversation
2. Technical screen (coding, 45 min)
3. Second round: Three 45-minute interviews
4. Leadership interview with senior engineer
- Focus: System design, code quality, decision-making under constraints
- Problems drawn from real systems: order books, matching engines, market-data pipelines
- C++ is the primary interview language

### Compensation

| Role | Level | Base | Total Comp |
|------|-------|------|------------|
| Quant Trader | Intern | $155–180K | $185–215K |
| Quant Developer | Intern | $150–175K | $175–200K |
| Quant Trader | New Grad | $175–200K | $325–425K |
| Quant Developer | New Grad | $160–185K | $260–350K |
| Quant Trader | Mid-Level | $200–250K | $475–750K |
| Quant Developer | Mid-Level | $185–240K | $375–600K |
| Quant Trader | Senior | $225–300K | $700K–$1.4M |

---

## 3. Jump Trading

### Overview

| Attribute | Detail |
|-----------|--------|
| Founded | 1999 (Chicago) |
| Type | Proprietary trading |
| Employees | ~1,000+ |
| Offices | Chicago, New York, London, Amsterdam, Singapore, Shanghai, Sydney |
| Infrastructure Investment | ~$850M (2024–2026 period) |
| HPC Commitment | ~$2.3B over 3 years (12,000 GPU nodes, Nvidia H100) |
| Data Lake | 45 PB projected |
| Subsidiary | World Class Wireless (microwave networks) |

### Latency Infrastructure

- **Custom microwave/millimeter-wave networks** — owns towers via World Class Wireless
- **FPGA-based network cards** with on-chip inference
- **12 new colocation data centers** added across NA, Europe, Asia (2024–2026)
- **200 Gbps InfiniBand switches** for inter-node fabric
- **Quantum-ready research cluster**
- **Three generations of GPU-accelerated AI inference engines**
- **18 ns latency reduction** on equities exchanges, **24 ns** on crypto matching engines (measured improvement from AI-driven upgrade)
- **1.2 μs median round-trip** for price-prediction pipeline (FPGA-based)
- **<2 μs round-trip** for equity venues, **<0.8 μs** on select crypto matching engines

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Core Trading | Highly optimized C++ (template-heavy, close-to-metal) |
| Hardware | Xilinx UltraScale+ FPGAs (2019–2023 migration) |
| ML Inference | Quantized neural networks (2–4 hidden layers, 8-bit weights) on FPGA |
| Research | Python, Kdb+ (petabyte-scale analysis) |
| HPC | 12,000 Nvidia H100 GPU nodes, custom FPGA accelerators |
| Network | Proprietary microwave (World Class Wireless), 200 Gbps InfiniBand |
| AI/ML | Deep RL agents, transformer-based market-state embeddings, gradient-boosted decision trees |

### Known Benchmarks

- 1.2 μs median round-trip (FPGA price-prediction pipeline)
- 1.7 μs equivalent CPU-GPU setup (for comparison)
- 30% reduction in end-to-end decision latency from FPGA-based ML vs. CPU-GPU
- 32% MAE reduction in order-flow prediction vs. pre-AI baseline
- Sub-μs inference on FPGA (partial reconfiguration for model updates)

### Hiring Profiles

**Software Engineer (Trading):**
- Bachelor's/Master's in CS, Engineering, or related
- 5+ years C++ development with algorithmic trading systems
- Track record in market order execution algorithms
- Experience with large-scale big data processing on HPC clusters

**FPGA Engineer:**
- VHDL or Verilog expertise
- Digital signal processing knowledge
- Understanding of financial markets
- Xilinx or Intel (Altera) toolchain experience
- Hand-written HDL preferred over HLS

**ML Research Engineer:**
- Python and/or C++ proficiency
- PyTorch, JAX, or TensorFlow
- GPU/accelerator programming (CUDA, Triton, SYCL, ROCm)
- Large-scale ML systems (hundreds of TB training data)

**Interview Process:**
- Timed online test: 2–3 algorithmic coding problems (C++/Python, 60–90 min)
- Phone screens: 45–60 min (live coding for engineers, probability/stats for quants)
- Onsite: System design, deep technical questions
- Acceptance rate: **<5%**
- Process duration: 4–8 weeks

### Compensation

| Role | Entry Total Comp | Senior Total Comp |
|------|-----------------|-------------------|
| Quantitative Researcher | $300–500K | $500K–$1.5M+ |
| Quantitative Trader | $300–600K | $600K–$2M+ |
| Software Engineer | $250–400K | $400–800K |
| FPGA Engineer | $280–450K | $500K–$1M |

---

## 4. Hudson River Trading (HRT)

### Overview

| Attribute | Detail |
|-----------|--------|
| Founded | 2000 (New York) |
| Type | Multi-asset quantitative trading |
| Employees | ~1,000 |
| Offices | 14 offices worldwide (6 countries) |
| Markets | 200+ markets |
| Culture | "Built by coders, led by coders" |
| AMD Partnership | AMD EPYC processors + AMD FPGAs |

### Latency Infrastructure

- **FPGA-based trading systems** with custom verification
- **SystemVerilog** for hardware design
- **Cocotb** (Python) for FPGA testbench co-simulation
- **Custom Linux kernel** optimizations
- **Matching-engine simulator** with <10 ns granularity data structure alignment
- **CoreWeave partnership** for AI research (NVIDIA Vera Rubin NVL72, HGX B200)
- **Spectrum-X Ethernet** for high-throughput direct connect
- **Open-source contributions**: slang-server (SystemVerilog language server), corral (C++20 structured concurrency), wavetools (Rust waveform analysis)

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Core Trading | C++ (low-level, cache-aware) |
| Hardware | SystemVerilog, AMD FPGAs |
| Verification | Cocotb (Python), C++ testbenches |
| Research | Python (custom fork, PEP 690 for faster imports) |
| Infrastructure | Custom Linux kernels, kernel bypass |
| AI/ML | NVIDIA Vera Rubin NVL72, HGX B200 on CoreWeave |
| Open Source | slang-server, corral, heracles-ql, wavetools, pymetabind |

### Known Benchmarks

- <10 ns granularity in matching-engine simulator data structures
- Custom Python fork for faster imports (PEP 690)
- AMD EPYC + AMD FPGA for financial algorithm acceleration

### Hiring Profiles

**Algorithm Developer (Quant Research & Trading):**
- Full-time undergrad or master's in quantitative discipline (math, physics, CS, statistics)
- Experience programming in Python and/or C++
- Experience with statistical analysis, numerical programming, or ML
- Strong analytical and problem-solving skills
- Base salary: **$250K** (official posting)

**Software Engineer:**
- Strong C++ fundamentals
- Low-level systems programming
- Cache-aware data structures
- Kernel bypass / network programming experience valued

**FPGA Engineer:**
- SystemVerilog/Verilog expertise
- Hardware design and verification
- Network protocol knowledge

**Interview Process:**
- Signature filter: n→N proof brainteasers
- Required C++ for QR roles
- Focus on probability, statistics, and low-level systems
- Known for exceptionally difficult technical interviews

### Compensation

| Role | Level | Base | Total Comp |
|------|-------|------|------------|
| Software Engineer | L1 (0–2 yrs) | $200K | $350–550K |
| Software Engineer | L2 (2–5 yrs) | $225K | $500–900K |
| Software Engineer | L3 (5–10 yrs) | $250K | $750K–$1.8M |
| Software Engineer | L4 (10+ yrs) | $275K+ | $1.5M–$5M |
| Software Engineer | L5 (15+ yrs) | $300K+ | $3M–$15M+ |
| Quant Researcher | Junior | $200K | $350–550K |
| Quant Researcher | Mid | $225K | $500K–$1M |
| Quant Researcher | Senior | $250K | $800K–$2M |
| Quant Researcher | Staff | $275K+ | $1.5M–$10M+ |

**Note:** HRT's new-grad packages include sign-on + first-year guarantee pushing total year-1 comp into $350K+ range. Bonuses vest quarterly with portions deferred across 8 quarters.

---

## 5. Tower Research Capital

### Overview

| Attribute | Detail |
|-----------|--------|
| Founded | 1998 (New York) |
| Type | Proprietary quantitative trading |
| Employees | ~1,484 |
| Offices | New York, London, Gurgaon, Singapore, Shanghai |
| Platform | High-performance technology platform shared across teams |

### Latency Infrastructure

- **Low-latency programming** in C++ (market data, execution, low-level infrastructure)
- **FPGA technology** and hardware acceleration
- **Rust** increasingly used for infrastructure and services
- **Python** for research, data analysis, orchestration
- **Core Engineering** team builds shared infrastructure; trading teams plug into platform
- **Global platform** supporting ultra-low latency and data-intensive approaches
- **Build systems**: Bazel, Buck2, CMake
- **Cloud**: AWS, GCP (for non-latency-critical workloads)

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Core Trading | C++ (latency-sensitive), Rust (infrastructure) |
| Research | Python, PyTorch, JAX, TensorFlow |
| Hardware | FPGA, hardware acceleration |
| Build | Bazel, Buck2, CMake |
| Cloud | AWS (EC2, VPC, ELB, S3, EBS), GCP |
| Data | Kafka, SQL, ETL pipelines |
| ML | Foundation models for markets (HAIL team), GPU/HPC clusters |

### Known Benchmarks

- Engineers solve problems in "low-latency programming, FPGA technology, hardware acceleration and machine learning"
- Continuous investment in "data platform, machine learning, low-latency programming, and electronic trading infrastructure"

### Hiring Profiles

**Software Engineer (Trading Systems):**
- Strong C++ fundamentals (data structures, algorithms)
- Linux/Unix systems
- Low-latency programming experience
- Python and shell scripting

**Software Engineer (Research Platform):**
- MSc or PhD in Computer Science
- 2+ years experience outside academia
- Familiarity with type systems and their implementation
- Experience with compilation techniques (IR design, lowering, optimization)
- C++ and performance optimization
- Rust and/or Python appreciated
- DSL/programming language design experience a plus

**Quantitative Researcher:**
- Strong mathematics and statistics background
- Python and/or C++
- Time series analysis, signal processing, econometrics
- ML model development

**Interview Process:**
- Technical screen focusing on C++ and systems
- Onsite with design, programming, code review
- Emphasis on low-latency systems thinking

### Compensation

| Role | Level | Base | Total Comp |
|------|-------|------|------------|
| Quant Trader | Intern | $155K | $185K |
| Quant Developer | Intern | $150K | $175K |
| Quant Trader | New Grad | $180K | $370K |
| Quant Developer | New Grad | $165K | $295K |
| Quant Trader | Mid-Level | $225K | $640K |
| Quant Trader | Senior | $265K | $1.1M |
| SWE (Research Platform) | Experienced | $150–250K | — |
| SWE (Trading Systems) | Experienced | ~$285K | — |

**India (Gurgaon):** ₹40–121 LPA range for SWE roles (top 3–5 highest-paying engineering employers in India).

---

## 6. Optiver

### Overview

| Attribute | Detail |
|-----------|--------|
| Founded | 1986 (Amsterdam) |
| Type | Global market maker (options specialty) |
| Employees | ~2,000–2,896 |
| Offices | Amsterdam (HQ), Chicago, Austin, Sydney, Shanghai, Taipei, Mumbai, London |
| Operating Income (2024) | >$5B |
| Specialty | Options market-making on virtually every major option venue |
| Data | Petabytes processed daily |
| Instruments | 1M+ financial instruments priced |

### Latency Infrastructure

- **FPGA-first approach**: Xilinx FPGAs for option quoting in Chicago and Sydney
- **<500 ns reaction time** for options quoting engine (Verilog team)
- **C++ with heavy template metaprogramming** — Greeks unrolled at compile time
- **Custom Linux kernels** and kernel bypass
- **Global trading network**: 16 data centers across Europe and Americas, 40 trading WAN lines, ~75,000 km of fiber
- **Leased wavelength services** on long-distance fiber (dedicated lanes, 100 Gbps)
- **Physical path diversity**: Multiple diverse paths, separate entry points at data centers
- **Automatic reroute** on fiber cut via backup paths
- **AMD hardware partnership**

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Core Trading | C++ (template metaprogramming, compile-time Greeks) |
| Hardware | Xilinx FPGAs (Verilog), bespoke hardware |
| Research | Python, systematic ML |
| Network | Leased wavelengths, 100 Gbps, microwave |
| Data | High-throughput data platforms (custom, not Kafka for latency-critical) |
| CI/CD | Custom tooling, Kubernetes, Postgres |
| ML/AI | AI-first mindset, deep learning, LLMs, reinforcement learning |

### Known Benchmarks

- **<500 ns** options quoting engine reaction time
- **1M+** financial instruments priced
- **Petabytes** of data processed daily
- **100 Gbps** trading WAN lines
- **75,000 km** of fiber in global network

### Hiring Profiles

**Trader:**
- Strong quantitative aptitude, fast mental math
- STEM background (math, physics, CS, engineering, statistics)
- No prior finance/trading experience required
- Intensive training program (Global Optiver Academy)
- Interviews: 80-in-8 mental math test, sequences pre-screens, card-counting simulations

**Quantitative Researcher:**
- Master's or PhD in mathematics, physics, statistics, or related
- Deep learning, LLMs, statistical modelling, reinforcement learning
- Strong programming (Python)

**Software Engineer:**
- C++ for performance-critical code
- Python for research tooling and internal platforms
- Low-latency systems design

**Hardware Engineer:**
- FPGA/ASIC design (Verilog, SystemVerilog, VHDL)
- Network protocol understanding
- AMD/Xilinx toolchain experience

**Interview Process:**
- 80-in-8 mental math pre-screen
- Sequences test
- Multiple technical rounds
- Trading simulations (card-counting, medallion-trading)
- Intensive onboarding via Global Optiver Academy

### Compensation

| Role | Level | US Total Comp | UK Total Comp |
|------|-------|--------------|---------------|
| Trader | Graduate | $250–400K | — |
| Trader | Senior | $400–700K+ | — |
| Quant Researcher | Graduate | $220–380K | £90–160K |
| Quant Researcher | Mid | $350–550K | £160–300K |
| Quant Researcher | Senior | $500–800K+ | £280–550K+ |
| Software Engineer | Graduate | $180–280K | £75–130K |
| Software Engineer | Mid | $280–420K | £130–220K |
| Software Engineer | Senior | $400–650K | £220–400K |

**Bonus Structure:** Global profit pool — all desks, all offices, pooled, then desk-blended before individual differentiation. No equity/deferred stock; upside comes from trading P&L.

**Amsterdam:** ~$460K TC across seniority; ~$205K average (Glassdoor, 97 trader reports).  
**Chicago/Austin:** ~$400K first-year TC; senior traders up to ~$755K.  
**Sydney:** ~A$225K typical graduate; 90th percentile near A$115K + ~A$200K average additional pay.

---

## 7. IMC Trading

### Overview

| Attribute | Detail |
|-----------|--------|
| Founded | 1989 (Amsterdam) |
| Type | Global market maker |
| Employees | 1,000+ |
| Offices | Amsterdam (HQ), Chicago, Sydney, Mumbai |
| Revenue (2025) | $3.12B (estimated) |
| Technology | Java (bulk), C++ (latency-critical), FPGA |
| HPC Expansion | 5x on-premises HPC cluster expansion (2025) |

### Latency Infrastructure

- **FPGA-based trading** for lowest possible latencies
- **Microwave links** in trading infrastructure
- **Java-based company** with C++ and FPGA for latency-critical paths
- **ML models executed directly on FPGA** — bypassing software stack latency
- **5x HPC cluster expansion** (2025) for AI-driven liquidity
- **40% increase in net trading revenue** correlated with compute expansion
- **AI integration** across entire stack: hardware-level FPGA optimizations to high-level strategy design

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Core Trading | Java (bulk), C++ (latency-critical) |
| Hardware | FPGA (Verilog, SystemVerilog, VHDL), ASIC design |
| Research | Python, AI/ML agents, ETL pipelines |
| Network | Microwave links, exchange connectivity |
| Data | Large-scale network captures (TB/day) |
| ML/AI | Deep learning on FPGA, self-optimizing liquidity systems |

### Known Benchmarks

- FPGA-based ML inference at nanosecond level
- 480 ns average latency (IEEE 2024 FPGA study — industry representative)
- 150,000 orders/second throughput (FPGA)
- 5x compute expansion → 40% revenue increase (2025)

### Hiring Profiles

**FPGA Engineer:**
- Bachelor's, Master's, or PhD in EE, CE, CS, or related
- 2+ years FPGA/ASIC design, testing, verification
- SystemVerilog/Verilog, C++, Python
- Linux environment
- Network and system-level protocols, packet-based data processing
- Computer architecture understanding
- Financial services familiarity a plus

**Software Engineer (Early Career):**
- 1–3 years post-graduation
- BA/BSc/MA/MSc in Engineering, CS, or related
- Strong algorithms and data structures
- Java or C++ proficiency
- Strong analytical skills

**Quantitative Developer:**
- 3–7 years quantitative software development
- Python and C++ production experience
- Probability, statistics, time series analysis
- ML concepts for systematic strategies
- Low-latency systems experience valuable

**Performance Engineer:**
- 3+ years in distributed systems, networks, OS internals, or ULL environments
- Python/C++ for analysis platforms
- Large-scale network captures (TB/day)
- Statistical modeling
- Latency measurement and optimization

**Interview Process:**
- Quantitative aptitude tests
- Coding assessments
- Multiple technical rounds (probability, math, market-making concepts)
- Graduate programs and internships available

### Compensation

| Role | Level | Total Comp |
|------|-------|------------|
| Graduate (all roles) | Entry | $200–350K |
| Experienced | Senior | $350–500K+ |
| Software Engineer (Early Career) | Entry | $200K base |

**Note:** IMC's compensation bands are industry estimates from aggregated public signals. Base salary + discretionary bonus structure.

---

## 8. Cross-Firm Comparison

### Latency Infrastructure Comparison

| Firm | Microwave Network | FPGA | Kernel Bypass | Custom Hardware | AI/ML on FPGA |
|------|------------------|------|---------------|-----------------|---------------|
| Citadel Securities | ✅ (private) | ✅ | ✅ | ✅ | ✅ |
| Jump Trading | ✅ (World Class Wireless) | ✅ | ✅ | ✅ (in-house HW team) | ✅ (on-chip inference) |
| HRT | — | ✅ | ✅ | ✅ | ✅ (AMD partnership) |
| Tower Research | — | ✅ | ✅ | — | ✅ (GPU/HPC) |
| Optiver | ✅ (leased wavelengths) | ✅ | ✅ | ✅ (bespoke) | ✅ (AMD partnership) |
| IMC Trading | ✅ | ✅ | ✅ | — | ✅ (deep learning on FPGA) |

### Technology Stack Comparison

| Firm | Primary Language | Hardware Description | ML Framework | Unique Tech |
|------|-----------------|---------------------|--------------|-------------|
| Citadel Securities | C++ | Solarflare/Xilinx, Mellanox | Transformers | Kdb+ |
| Jump Trading | C++ | Xilinx UltraScale+ | PyTorch, JAX, CUDA | World Class Wireless, quantized NN on FPGA |
| HRT | C++ | AMD EPYC + AMD FPGA | — | Cocotb, slang-server, corral |
| Tower Research | C++, Rust | FPGA | PyTorch, JAX, TensorFlow | Bazel/Buck2, HAIL team |
| Optiver | C++ | Xilinx FPGA | DL/LLM/RL | Template metaprogramming (compile-time Greeks) |
| IMC Trading | Java, C++ | FPGA (Verilog/SV/VHDL) | AI/ML agents | 5x HPC expansion |

### New Grad Total Compensation Comparison (US, 2026)

| Firm | Role | Year 1 Total Comp |
|------|------|-------------------|
| Citadel Securities | Quant Trader | $325–425K |
| Citadel Securities | Quant Developer | $260–350K |
| Jump Trading | Quant Researcher | $300–500K |
| Jump Trading | Software Engineer | $250–400K |
| HRT | Software Engineer | $350–550K |
| HRT | Quant Researcher | $350–550K |
| Tower Research | Quant Trader | ~$370K |
| Tower Research | Quant Developer | ~$295K |
| Optiver | Trader | $250–400K |
| Optiver | Quant Researcher | $220–380K |
| Optiver | Software Engineer | $180–280K |
| IMC Trading | Graduate | $200–350K |

### Hiring Difficulty & Selectivity

| Firm | Acceptance Rate | Key Filter | Interview Style |
|------|----------------|------------|----------------|
| Citadel Securities | <5% | C++ expertise, system design | Design → Code → Code Review → Discussion |
| Jump Trading | <5% | Deep C++, HDL, probability | Timed coding → Phone screens → Onsite |
| HRT | <5% | n→N proofs, C++ required | Brainteasers + deep technical |
| Tower Research | ~5–10% | C++, low-latency systems | Technical + design |
| Optiver | <5% | 80-in-8 mental math, sequences | Math-heavy + trading simulations |
| IMC Trading | ~5–10% | Quantitative aptitude, coding | Multi-round technical |

---

## 9. Key Technology Patterns

### 1. FPGA Dominance
All six firms use FPGAs for the latency-critical path. The consensus architecture:
- **FPGA handles**: Market data decoding, order book updates, pre-trade risk checks, order encoding
- **CPU handles**: Strategy logic, parameter updates, position tracking, P&L
- **Key insight**: FPGAs provide determinism, not just speed — the same work in the same number of cycles every time

### 2. Kernel Bypass
Two dominant stacks:
- **Solarflare/Xilinx Onload + ef_vi** (now AMD)
- **Mellanox/NVIDIA Connect-X + DPDK** (now NVIDIA)
- **RoCE** (RDMA over Converged Ethernet) for inter-node fabric

### 3. Microwave Networks
- Speed of light in air ≈ 50% faster than fiber
- Chicago ↔ New York: 4.7 ms (microwave) vs 7.2 ms (fiber)
- Key operators: World Class Wireless (Jump), McKay Brothers, New Line Networks
- Single route lease: >$10M/year

### 4. AI/ML Integration
- **Jump Trading**: Quantized neural networks on FPGA (2–4 layers, 8-bit weights), 1.2 μs inference
- **HRT**: NVIDIA Vera Rubin NVL72 on CoreWeave for research
- **Optiver**: AI-first mindset, deep learning, LLMs, RL
- **IMC**: Deep learning on FPGA, 5x HPC expansion
- **Citadel**: Transformer-based signal models
- **Tower**: Foundation models for markets (HAIL team), GPU/HPC clusters

### 5. Language Trends
- **C++**: Still dominant for latency-critical code (all firms)
- **Rust**: Emerging for infrastructure (Tower, HRT open-source)
- **Python**: Universal for research and tooling
- **Java**: IMC's bulk systems (unique among the group)
- **SystemVerilog/Verilog**: Hardware description (all firms with FPGA teams)

### 6. Verification & Testing
- **HRT**: Cocotb (Python) for FPGA co-simulation, C++ testbenches
- **IMC**: Automated testing and verification
- **Industry**: UVM (Universal Verification Methodology) popular but HRT prefers C++/Python approach

---

## 10. Sources

- HFT Firms 2026 Deep-Dive (youngju.dev, labhub.hopto.org)
- Citadel Securities careers pages and business model analysis
- Jump Trading technology articles (finexus.net, eathealthy365.com)
- HRT official site, tech blog, GitHub, AMD case study, CoreWeave partnership
- Tower Research Capital careers pages, NUS career fair, job postings
- Optiver technology pages, Pragmatic Engineer newsletter, global trading network article
- IMC Trading careers pages, Built In Chicago spotlight, Canary Wharfian job postings
- IEEE 2024 FPGA for HFT study
- Algo-Logic Systems CME T2T press release
- CSPi Tick-to-Trade latency benchmark
- Quant Blueprint, Quantt, QuantVault salary aggregators
- Levels.fyi compensation data
- Ars Technica: "The secret world of microwave networks" (2016)
- McKay Brothers / Quincy Data microwave network press releases
- techinterview.org: FPGA interview guide, trading system architecture

---

*Report compiled from publicly available sources including company career pages, tech blogs, academic papers, salary aggregators, and trade press. Compensation figures are estimates and vary by role, location, performance, and year. Latency benchmarks are from published studies and may not reflect current production systems.*
