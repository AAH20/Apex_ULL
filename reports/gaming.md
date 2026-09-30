# Ultra-Latency Gaming Research Report

**Date:** 2026-09-29  
**Scope:** NVIDIA, AMD, Intel, Qualcomm, ARM, Apple  
**Metrics:** Latency, Throughput, Availability, Cost, Market Share

---

## Executive Summary

The gaming silicon landscape is bifurcated: **discrete PC GPUs** (NVIDIA dominant at 92–94% market share) and **mobile/integrated gaming** (Apple, Qualcomm, ARM, Samsung, Sony). NVIDIA leads in raw throughput and latency-reduction software (Reflex 2: up to 75% latency cut). AMD trails in market share (5–8%) but offers competitive latency tech (Anti-Lag 2). Intel is a distant third (~1% discrete GPU share). In mobile, Apple's A-series/M-series chips dominate revenue; Qualcomm's Snapdragon leads Android gaming; ARM's Mali/Immortalis GPUs underpin most non-Apple mobile gaming.

---

## 1. NVIDIA

### Latency
| Metric | Value | Source |
|--------|-------|--------|
| Reflex 2 (Frame Warp) max reduction | **75%** (e.g., 56ms → 14ms in THE FINALS @4K) | NVIDIA CES 2025 |
| Reflex Low Latency mode | ~50% average reduction | NVIDIA |
| VALORANT w/ Reflex 2 | **<3ms** PC latency (800+ FPS, RTX 5090) | NVIDIA |
| CS2 w/ Reflex | **6ms** latency (RTX 40-series, 478 FPS) | NVIDIA |
| Overwatch 2 w/ Reflex | **5ms** latency (RTX 4090, ~600 FPS) | NVIDIA |
| Marvel Rivals w/ Reflex | **9.7–11.3ms** (RTX 50-series, 1080p–1440p) | NVIDIA |
| Local rendering avg (Reflex Analyzer) | **6.2ms** | Industry measurement |
| Cloud-streamed (GeForce NOW) | **42–89ms** (ISP-dependent) | Industry measurement |

### Throughput
| Product | FP16 Compute | Memory | Notes |
|---------|-------------|--------|-------|
| RTX 5090 | ~112 TFLOPS (pre-release validation) | 32 GB GDDR7 | Blackwell |
| RTX 4090 | 63.1 TFLOPS | 24 GB GDDR6X | Ada Lovelace |
| RTX 5080 | ~50+ TFLOPS | 16 GB GDDR7 | Blackwell |

### Availability
- **Market share (discrete GPU):** 92% (Q1 2025) → 94% (Q2 2025) → 94% (Q4 2025) — all-time high
- **Overall PC GPU (incl. iGPU):** ~80%+
- **Steam Hardware Survey:** RTX 3060 + 4060 alone = ~9% each
- **Gaming revenue:** $3.8B in Q1 2025 (record, +42% YoY, +48% QoQ)
- **2025 total dGPU shipments:** ~44.28M units (NVIDIA ~94% = ~41.6M)

### Cost
- RTX 5090 MSRP: $1,999 | RTX 5080: $999 | RTX 5070 Ti: $749 | RTX 5070: $549 | RTX 5060 Ti: $349
- Real-world pricing often 20–40% above MSRP due to tariffs and demand
- **Cost per TFLOPS (FP16):** ~$18 (RTX 5090) to ~$40 (RTX 5060)

### Key Technologies
- **NVIDIA Reflex 2** (Frame Warp): updates rendered frame with latest mouse input pre-display
- **DLSS 5** (Neural Rendering): AI upscaling + frame generation
- **G-SYNC:** hardware module for variable refresh, ultra-low latency
- **GeForce NOW:** cloud gaming (42–89ms latency)

---

## 2. AMD

### Latency
| Metric | Value | Source |
|--------|-------|--------|
| Anti-Lag 2 max reduction | **54%** lower latency (HYPR-RX) | AMD |
| Anti-Lag (driver-level) | Up to 33% improvement | AMD |
| Enhanced Sync vs VSync | 39.2ms vs 80.7ms response time | AMD |
| Ryzen 9 7950X3D frame-time variance | **-37%** vs non-3D (open-world titles) | Industry |

### Throughput
| Product | Compute | Memory | Notes |
|---------|---------|--------|-------|
| RX 9070 XT | ~94.7 TFLOPS (FP16) | 16 GB GDDR7 @ 32 Gbps | RDNA 4 |
| RX 7900 XTX | ~61 TFLOPS | 24 GB GDDR6 | RDNA 3 |

### Availability
- **Market share (discrete GPU):** 8% (Q1 2025) → 6% (Q2 2025) → 5% (Q4 2025) — all-time low
- **2025 dGPU shipments:** ~2.2M units (5% of 44.28M)
- **Radeon 9000 series:** <750K units shipped in Q1 2025
- **CPU side:** 40.31% Steam survey share (May 2025) vs Intel 59.69%

### Cost
- RX 9070 XT: $549 MSRP | RX 9070: $499 MSRP
- **Cost per TFLOPS:** ~$6 (RX 9070 XT) — significantly better value than NVIDIA
- AMD's challenge: scarce availability at MSRP, fake MSRPs persist 5+ months post-launch

### Key Technologies
- **Anti-Lag 2:** in-game frame pacing, developer-integrated (CS2, Dota 2, Ghost of Tsushima)
- **HYPR-RX:** one-click profile enabling Anti-Lag + Boost + Chill
- **FSR 4:** AMD's upscaling answer to DLSS
- **FreeSync:** open-standard VRR (no hardware module cost)

---

## 3. Intel

### Latency
| Metric | Value | Source |
|--------|-------|--------|
| Xe Low Latency (XeLL) max reduction | **45%** vs standard rendering | Intel XeSS 2 whitepaper |
| XeLL + XeSS-SR combined | Further reduction (up to 3.9x FPS boost) | Intel |
| Cyberpunk 2077 (Arc A770) | 79ms → 37ms with XeLL | Notebookcheck |
| 4x MFG + XeLL | 56ms (still 28% lower than no FG/no XeLL) | Notebookcheck |

### Throughput
| Product | Compute | Memory | Notes |
|---------|---------|--------|-------|
| Arc B580 | ~20+ TFLOPS | 12 GB GDDR6 | Battlemage |
| Arc A770 | ~18 TFLOPS | 16 GB GDDR6 | Alchemist |

### Availability
- **Market share (discrete GPU):** 0% (Q1 2025) → <1% (Q2 2025) → 1% (Q3 2025)
- **Battlemage B-series:** launched Q4 2024, failed to move share needle
- **CPU side:** 59.69% Steam survey share (May 2025), down from 65–70% historically
- **Client Computing Group revenue:** $7.9B (Q2 2025, -3% YoY)

### Cost
- Arc B580: $249 MSRP | Arc A770: $329 MSRP
- **Cost per TFLOPS:** ~$12 (Arc B580) — competitive on paper, limited by software ecosystem

### Key Technologies
- **XeSS 2** (Super Resolution + Frame Generation + Low Latency)
- **XeLL:** application-integrated low-latency mode
- **Driver Low Latency Mode:** for older games without XeLL integration
- **Intel Killer Wi-Fi:** network-level latency optimization

---

## 4. Qualcomm

### Latency
| Metric | Value | Source |
|--------|-------|--------|
| Snapdragon 8 Gen 3 touch-to-display | **18.7–23.7ms** (120Hz mode) | Lab testing |
| aptX Low Latency (Bluetooth audio) | **38–42ms** (both ends LL-compliant) | Qualcomm |
| 5G uplink latency (C-Band) | **14.2ms** median (lab), 32.7ms (urban peak) | Qualcomm/Verizon |
| Cloud gaming (Snapdragon G3 Gen 3) | Wi-Fi 7 support for reduced latency | Qualcomm |
| Game Turbo 8.0 target | **<50ms** end-to-end by 2025 | Qualcomm roadmap |

### Throughput
| Product | CPU | GPU | Notes |
|---------|-----|-----|-------|
| Snapdragon 8 Elite | Oryon cores | Adreno 8-series | Flagship |
| Snapdragon G3 Gen 3 | +30% vs G3 Gen 2 | +28% vs G3 Gen 3 | Handheld gaming |
| Snapdragon G2 Gen 2 | 2.3x vs G2 Gen 1 | 3.8x vs G2 Gen 1 | Cloud gaming 144FPS |
| Snapdragon G1 Gen 2 | +80% vs G1 Gen 1 | +25% vs G1 Gen 1 | 1080p@120FPS cloud |

### Availability
- **Smartphone SoC share:** ~25–30% global (behind Apple in revenue, ahead in unit volume)
- **Handheld gaming:** AYANEO, ONEXSUGAR, Retroid Pocket adopting G Series
- **AI PC (Snapdragon X Elite):** 0.8% market share (Q3 2024, 720K units)
- **Revenue:** $10.37B (Q3 FY2025, +10% YoY)

### Cost
- Snapdragon 8 Elite devices: $800–$1,200 (flagship tier)
- Snapdragon G Series handhelds: $300–$700
- **Cost efficiency:** Best-in-class perf/watt for mobile

### Key Technologies
- **Snapdragon Sound:** aptX LL, aptX Adaptive for low-latency audio
- **Game Turbo:** system-level gaming optimization
- **Wi-Fi 7:** reduced network latency for cloud gaming
- **Lumen/Unreal Engine 5 support:** first on Android handhelds (G3 Gen 3)

---

## 5. ARM

### Latency
| Metric | Value | Source |
|--------|-------|--------|
| Binary translation overhead (ARM→x86) | **+5–15ms** input lag | Industry analysis |
| Frame time increase (emulator) | 16.67ms → 20–25ms (15–30% overhead) | Industry analysis |
| KleidiAI + ONNX Runtime | **2.3x** performance improvement, low power | Arm |
| Neural Super Sampling (NSS) | Reduces GPU workload by up to **50%** | Arm |

### Throughput
| Product | Architecture | Notes |
|---------|-------------|-------|
| Mali-G720 | 5th Gen, Deferred Vertex Shading | -40% geometry memory traffic |
| Immortalis-G925 | Fragment Prepass | -43% shader workload |
| Mali-G1 Ultra (2025) | RTUv2 (Single Ray) | +119% ray tracing perf |
| Cortex-X925 | +15% IPC | Flagship CPU core |

### Availability
- **Overall CPU market share:** 11.9% (Q1 2025, first time >10%)
- **Notebook CPU share:** 13.9% (Q1 2025, up from 10.9% end 2024)
- **Server CPU share:** 13.2% (Q1 2025, driven by NVIDIA Grace)
- **Mobile GPU:** Powers ~100% of non-Apple smartphones (via MediaTek, Samsung, Qualcomm SoCs)

### Cost
- ARM IP licensing: royalty-based (per-chip fee)
- **Cost model:** Licensing revenue ~$2B/year; chip partners bear manufacturing cost
- **Cost efficiency:** ARM's business model is low-margin per unit but massive scale

### Key Technologies
- **Neural Super Sampling (NSS):** AI upscaling, 50% GPU workload reduction
- **Arm ASR (Accuracy Super Resolution):** spatial upscaling
- **RTUv2:** Single-ray tracing for mobile
- **KleidiAI:** on-device LLM inference for gaming NPCs
- **ExecuTorch:** on-device AI deployment

---

## 6. Apple

### Latency
| Metric | Value | Source |
|--------|-------|--------|
| iPhone 15 Pro touch-to-photon | **62.3ms** median (240Hz touch sampling) | Lab testing |
| iPhone 15 Pro Max | 62.3ms median, 9.2ms jitter | Lab testing |
| A17 Pro GPU render time | **6.4ms** @ 60FPS | Lab testing |
| iOS 17.4 OS processing | **3.2ms** average | Lab testing |
| Display scan-out (120Hz) | **8.3ms** | Lab testing |
| Total system latency (iPhone 15 Pro) | **18.7ms** (best-case) | Lab testing |
| MetalFX upscaling | 40 FPS → 100+ FPS (native-ported games) | Mac Research |

### Throughput
| Product | Compute | Memory | Notes |
|---------|---------|--------|-------|
| A17 Pro | ~35 TFLOPS (GPU) | 8 GB unified | 3nm |
| M5 (MacBook Pro) | ~40+ TFLOPS | 16–24 GB unified | 3nm |
| M3 Max | ~40 TFLOPS | 48 GB unified | 3nm |

### Availability
- **Mobile gaming revenue:** $52.5B (App Store, 2025) — more than Google Play + Steam combined
- **Google Play gaming revenue:** $30B (2025)
- **Steam gaming revenue:** $11.7B (2025)
- **Game downloads:** 15% (App Store) vs 81% (Google Play) — but 3.5x higher revenue per user
- **Services revenue:** >$30B/quarter (2nd largest after iPhone)
- **Mac gaming:** Growing but still niche vs Windows

### Cost
- iPhone 15 Pro: $999+ | MacBook Pro M5: $1,599+ | Mac Studio: $1,999+
- **Cost per TFLOPS:** ~$28 (A17 Pro) to ~$40 (M5)
- **Premium pricing:** Apple commands highest ASP in gaming hardware

### Key Technologies
- **Metal 4:** latest graphics API with ML integration
- **MetalFX Upscaling + Frame Interpolation:** AI-powered rendering
- **Game Porting Toolkit:** Windows game translation to macOS
- **Apple Silicon unified memory:** zero-copy CPU/GPU data sharing
- **240Hz touch sampling:** industry-leading input responsiveness

---

## 7. Samsung, Sony, Microsoft, Google (Brief)

### Samsung
- **Exynos 2400:** ARM Mali-G720 GPU, 84.7ms median latency (S24 Ultra)
- **Market share:** ~20% global smartphone (but losing to Chinese OEMs)
- **Gaming:** Galaxy S24 Ultra uses Snapdragon 8 Gen 3 (not Exynos) in most markets

### Sony (PlayStation)
- **PS5:** AMD Zen 2 + RDNA 2 (custom), 16 GB GDDR6
- **PS5 Pro:** Enhanced GPU, 2 TB SSD
- **Latency:** ~50–100ms (console + TV processing)
- **Market share:** ~45% console market (vs Xbox ~30%)

### Microsoft (Xbox)
- **Xbox Series X:** AMD Zen 2 + RDNA 2, 12 TFLOPS
- **Xbox Cloud Gaming:** 112.4ms median latency (35+ Mbps required)
- **Game Pass:** 25M+ subscribers

### Google
- **Google Play:** $30B gaming revenue (2025), 81% of downloads
- **Stadia:** Discontinued (2023) — cloud gaming latency was 80–150ms
- **Tensor G3:** ARM Mali-G715 GPU, 91.2ms median latency (Pixel 8 Pro)

---

## Comparative Summary

### Latency (Lower is Better)
| Platform | Best-Case Latency | Technology |
|----------|-------------------|------------|
| NVIDIA RTX 5090 + Reflex 2 | **<3ms** (VALORANT) | Frame Warp |
| AMD RX 9070 XT + Anti-Lag 2 | **~10–15ms** | In-game frame pacing |
| Intel Arc B580 + XeLL | **~37ms** (Cyberpunk) | Xe Low Latency |
| Apple A17 Pro (iPhone) | **18.7ms** | 240Hz touch + Metal |
| Qualcomm SD 8 Gen 3 | **18.7–23.7ms** | Game Turbo |
| ARM Mali-G720 (native) | **~20ms** | Native execution |
| Cloud (GeForce NOW) | **42–89ms** | ISP-dependent |
| Cloud (Xbox Cloud) | **112ms** | 35+ Mbps required |

### Market Share (Discrete GPU, Q4 2025)
| Company | Share | Trend |
|---------|-------|-------|
| **NVIDIA** | **94%** | ↑ +2 pts YoY |
| **AMD** | **5%** | ↓ -3 pts YoY |
| **Intel** | **1%** | ↑ +1 pt (first ever) |

### Revenue (Gaming, 2025)
| Company/Platform | Revenue | Notes |
|-----------------|---------|-------|
| **Apple App Store** | **$52.5B** | Mobile gaming IAP |
| **Google Play** | **$30B** | Mobile gaming IAP |
| **NVIDIA Gaming** | **~$15B/yr** | GPU sales |
| **Steam** | **$11.7B** | PC game sales |
| **AMD Gaming** | **~$2.9B/yr** | GPU + semi-custom |
| **Qualcomm QCT** | **~$36B/yr** | Handsets + IoT + Auto |

---

## Key Takeaways for Ultra-Low-Latency Infrastructure

1. **NVIDIA Reflex 2 is the gold standard** for PC gaming latency (<3ms achievable)
2. **Apple's unified memory + 240Hz touch** sets the mobile latency benchmark (18.7ms)
3. **Cloud gaming adds 40–120ms** over local rendering — still not viable for competitive FPS
4. **ARM's Neural Super Sampling** could reduce mobile GPU workload by 50% — major latency implication
5. **Binary translation adds 5–15ms** — critical for cloud/x86-on-ARM gaming workloads
6. **NVIDIA's 94% market share** means gaming optimization is overwhelmingly GeForce-first
7. **AMD's price/performance** is superior ($6/TFLOPS vs NVIDIA's $18/TFLOPS) but ecosystem lags
8. **Intel's XeLL** shows promise (45% reduction) but 1% market share limits developer adoption

---

## Sources
- Jon Peddie Research (JPR) Q1–Q4 2025 GPU market reports
- NVIDIA GeForce News (Reflex 2, CES 2025)
- AMD Radeon Anti-Lag 2 product page
- Intel XeSS 2 whitepaper (March 2025)
- Qualcomm Snapdragon G Series announcement (March 2025)
- Arm GDC 2025 blog, Arm gaming marketplace
- Apple Metal 4 developer documentation
- SensorTower State of Gaming 2026 report
- Steam Hardware Survey (May 2025)
- Mercury Research CPU market share (Q1 2025)
- Various lab measurements (thegadgetdigest, macresearch, notebookcheck)
