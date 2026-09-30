# Top 10 Ultra-Low-Latency Projects on GitHub

> Research compiled: 2026-09-30. Stars and metrics are approximate as of this date.

---

## 1. microsoft/garnet

| Field | Value |
|---|---|
| **Stars** | ~12,000 |
| **Language** | C# |
| **License** | MIT |
| **Category** | Remote cache-store |

**Latency Claims:** Sub-300μs p99 client latency on commodity Azure VMs with Accelerated Networking. Higher throughput than comparable open-source cache-stores.

**Benchmarks:** Microsoft Research papers and blog posts demonstrate throughput and latency improvements over Redis. Vector Sets (preview) with DiskANN show leading QPS, p99 latency, and recall.

**README Quality:** Excellent. Clear architecture diagrams, feature list, performance benchmarks, and deployment guides. Well-structured with quick-start examples.

**Demo Style:** No live demo. Documentation includes Docker deployment, Azure setup guides, and benchmark reproduction scripts.

---

## 2. ossrs/srs

| Field | Value |
|---|---|
| **Stars** | ~29,000 |
| **Language** | C++ |
| **License** | MIT |
| **Category** | Real-time media streaming server |

**Latency Claims:** Sub-second latency via WebRTC delivery. Supports RTMP, HLS, HTTP-FLV, SRT, MPEG-DASH, and GB28181.

**Benchmarks:** Community benchmarks show 5,000+ concurrent RTMP ingests with sub-400ms end-to-end LL-HLS latency. Docker Hub: 1.8M+ pulls.

**README Quality:** Very good. Comprehensive protocol support matrix, Docker quick-start, clustering docs, and ARM/RISC-V platform notes. Active community with 154 contributors.

**Demo Style:** Docker one-liner demo. Active documentation site (ossrs.io) with tutorials and configuration examples.

---

## 3. Haivision/srt

| Field | Value |
|---|---|
| **Stars** | ~3,100 |
| **Language** | C++ |
| **License** | MPL-2.0 |
| **Category** | Transport protocol (Secure Reliable Transport) |

**Latency Claims:** Sub-second (120-500ms typical) latency for live video over unreliable networks. Configurable latency budget (SRTO_LATENCY). Emmy Award 2022.

**Benchmarks:** Reference C++ implementation with published Internet Draft. SRT Alliance (~500 member companies) maintains interoperability tests. Typical deployments: 120-500ms at 10-50 Mbps.

**README Quality:** Good. Clear protocol overview, feature breakdown (Secure/Reliable/Transport), packet filter API docs, and FEC configuration. Some sections could be more beginner-friendly.

**Demo Style:** No hosted demo. Includes `srt-live-transmit` tool for testing. Extensive docs/ directory with feature guides.

---

## 4. kungfu-origin/kungfu

| Field | Value |
|---|---|
| **Stars** | ~3,900 |
| **Language** | C++ |
| **License** | Apache-2.0 |
| **Category** | Low-latency trading execution system |

**Latency Claims:** Microsecond-level system response. Nanosecond-precision time-series data storage via Yijinjing component. Zero-copy cross-language memory sharing.

**Benchmarks:** No formal public benchmarks. Architecture emphasizes lock-free ring buffers, shared-memory IPC, and non-blocking I/O for HFT workloads.

**README Quality:** Moderate. Feature list is comprehensive but assumes trading domain knowledge. Documentation site exists but could be more accessible to newcomers.

**Demo Style:** No live demo. Reference implementation for XTP gateway (China). SDKs for C++, Python, and Node.

---

## 5. PlatformLab/NanoLog

| Field | Value |
|---|---|
| **Stars** | ~3,400 |
| **Language** | C++ |
| **License** | BSD-2-Clause |
| **Category** | Nanosecond-scale logging system |

**Latency Claims:** 7ns median latency. 80+ million logs/second throughput. Published at USENIX ATC 2018.

**Benchmarks:** Extensive benchmark suite in `benchmarks/` directory. Compared against spdlog, g3log, Boost.Log, fmtlog, and others. Scripts reproduce paper figures.

**README Quality:** Good. Clear API examples, benchmark methodology, and comparison tables. Published paper adds credibility.

**Demo Style:** No live demo. Benchmark scripts and example code in repository. Strong academic backing.

---

## 6. OvenMediaEngine

| Field | Value |
|---|---|
| **Stars** | ~3,100 |
| **Language** | C++ |
| **License** | AGPL-3.0 |
| **Category** | Sub-second latency live streaming server |

**Latency Claims:** Sub-second latency via WebRTC. 2-5 seconds via LLHLS. Supports WHIP ingest from OBS 30+.

**Benchmarks:** Community reports: 5,000+ concurrent RTMP ingests with sub-400ms LL-HLS latency. Production deployment at Streamwell (broadcast SaaS).

**README Quality:** Very good. Comprehensive feature list (ingest/transcode/delivery/clustering/DRM), Docker quick-start, REST API docs, and WHIP integration guide.

**Demo Style:** OvenSpace demo service (space.ovenplayer.com). Docker deployment with single command. Active REST API for programmatic control.

---

## 7. odygrd/quill

| Field | Value |
|---|---|
| **Stars** | ~3,000 |
| **Language** | C++ |
| **License** | MIT |
| **Category** | Ultra-low-latency asynchronous logging |

**Latency Claims:** 6ns p50/p90 for number logging (bounded dropping queue). 9ns p95. Outperforms spdlog, Boost.Log, g3log, fmtlog in benchmarks.

**Benchmarks:** Detailed latency tables (p50-p99.9) comparing 10+ logging libraries. Throughput benchmarks: 6.44M msg/sec. Cross-platform (Linux, macOS, Windows, BSD).

**README Quality:** Excellent. Clear setup examples, latency benchmark tables, feature list (metrics, JSON, MDC, backtrace), and configuration options. Well-organized.

**Demo Style:** No live demo. Comprehensive benchmark suite in repository. Simple `simple_logger()` quick-start.

---

## 8. OpenHD

| Field | Value |
|---|---|
| **Stars** | ~2,400 |
| **Language** | C++ |
| **License** | GPL-3.0 |
| **Category** | FPV video transmission ( drones/robotics) |

**Latency Claims:** ~110ms minimum glass-to-glass on Raspberry Pi. ~125ms typical. 40-60ms possible on Jetson Nano with optimized camera.

**Benchmarks:** Community-tested on Raspberry Pi, Jetson Nano, and x86. Latency depends heavily on encoder/decoder hardware. H.265 encoding reduces latency further.

**README Quality:** Moderate. Hardware-focused documentation. GitBook docs site with FAQ, troubleshooting, and platform-specific guides. Assumes FPV domain knowledge.

**Demo Style:** No live demo. Hardware-dependent project. Active Discord community and Patreon for custom hardware development.

---

## 9. sonosaurus/sonobus

| Field | Value |
|---|---|
| **Stars** | ~2,100 |
| **Language** | C++ |
| **License** | GPL-3.0 |
| **Category** | Real-time P2P audio streaming |

**Latency Claims:** Low-latency audio streaming with configurable jitter buffer. Opus codec at 16-256 kbps per channel. Uncompressed PCM support.

**Benchmarks:** No formal benchmarks. Latency depends on network conditions and buffer settings. AOO (Audio over OSC) transport layer purpose-built for audio.

**README Quality:** Moderate. Clear use case description (musicians, podcasters). Configuration options for latency/quality tradeoff. No formal benchmarking section.

**Demo Style:** Standalone app (macOS, Windows, iOS, Linux) + AU/VST plugin. No hosted demo. Website (sonobus.net) with download links.

---

## 10. chronoxor/CppServer

| Field | Value |
|---|---|
| **Stars** | ~1,650 |
| **Language** | C++ |
| **License** | MIT |
| **Category** | Asynchronous socket server/client library |

**Latency Claims:** "Ultra fast and low latency" asynchronous I/O. Supports TCP, SSL, UDP, HTTP, HTTPS, WebSocket. 10K+ connections problem solution.

**Benchmarks:** Companion project CppBenchmark provides nanosecond-precision benchmarking with HDR histograms. No formal latency benchmarks in main README.

**README Quality:** Moderate. Build instructions for Linux/macOS/Windows. Example code for protocols. Assumes C++ and networking knowledge.

**Demo Style:** No live demo. Example code for each protocol. Companion projects (CppBenchmark, CppLogging, CppTrader) provide additional context.

---

## Summary Table

| # | Project | Stars | Language | Latency Claim | Category |
|---|---|---|---|---|---|
| 1 | microsoft/garnet | 12k | C# | Sub-300μs p99 | Cache-store |
| 2 | ossrs/srs | 29k | C++ | Sub-second (WebRTC) | Media streaming |
| 3 | Haivision/srt | 3.1k | C++ | 120-500ms | Transport protocol |
| 4 | kungfu-origin/kungfu | 3.9k | C++ | Microsecond-level | Trading system |
| 5 | PlatformLab/NanoLog | 3.4k | C++ | 7ns median | Logging |
| 6 | OvenMediaEngine | 3.1k | C++ | Sub-second (WebRTC) | Media streaming |
| 7 | odygrd/quill | 3.0k | C++ | 6-9ns p50-p95 | Logging |
| 8 | OpenHD | 2.4k | C++ | 110-125ms | FPV video |
| 9 | sonosaurus/sonobus | 2.1k | C++ | Configurable (Opus) | Audio streaming |
| 10 | chronoxor/CppServer | 1.6k | C++ | "Ultra fast" | Socket server |

---

## Key Observations

- **C++ dominates** ULL projects (8/10), with C# (Garnet) as the notable exception.
- **Logging** is a mature ULL sub-category with strong academic backing (NanoLog ATC 2018) and active competition (Quill vs NanoLog vs fmtlog).
- **Media streaming** (SRS, OvenMediaEngine, SRT) focuses on sub-second latency over WebRTC/LLHLS.
- **Trading systems** (Kungfu) prioritize microsecond/nanosecond response but lack public benchmarks.
- **README quality varies**: Garnet, SRS, OvenMediaEngine, and Quill have excellent documentation; trading/FPV projects assume domain expertise.
- **Demo availability**: Most projects lack live demos; Docker-based demos (SRS, OvenMediaEngine) and desktop apps (SonoBus) are the primary evaluation paths.
