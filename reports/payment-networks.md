# Payment Networks: Ultra-Latency Research Report

**Date:** 2026-09-29  
**Scope:** Visa, Mastercard, American Express, Discover, PayPal, Stripe, Square, Adyen, Worldpay, Fiserv

---

## Executive Summary

This report compiles latency, throughput, availability, cost, and market share data for the world's largest payment networks and processors. The data is sourced from company publications, SEC filings, technical blogs, and industry reports (Nilson Report, Statista) current as of 2024–2025.

---

## 1. Visa

| Metric | Value | Source |
|--------|-------|--------|
| **Latency** | <1 second (authorization); milliseconds for routing | VisaNet booklet |
| **Throughput (peak)** | 83,000 transaction messages/second | Visa corporate (2025) |
| **Throughput (annual)** | 322+ billion transactions; $16T payments volume | Visa corporate (2025) |
| **Availability** | 99.9999% ("six nines") — <1 sec downtime/day | Visa corporate |
| **Infrastructure** | 7 independent data centers; 1,600 secure network endpoints; 1.2M miles fiber | VisaNet booklet |
| **Cost** | Network fees charged to issuers/acquirers (not publicly disclosed) | — |
| **Market Share (US)** | 61.1% of card spending (2024) | Nilson Report |
| **Market Share (Global)** | ~32.8% of purchase volume | Nilson Report (2022) |

**Key Technical Details:**
- VisaNet is a centralized, modular payments network
- Processes 80 billion+ transactions annually (authorization + clearing)
- Domestic processing in 100+ countries
- NOC stress-test capacity exceeds 65,000 messages/second
- 120+ cyber controls; White House-level physical security

---

## 2. Mastercard

| Metric | Value | Source |
|--------|-------|--------|
| **Latency** | Milliseconds for authorization; real-time card payments via Transaction Stream | Mastercard (2025) |
| **Throughput** | Not explicitly published; 575B RTP transactions expected globally by 2028 | Mastercard (2024) |
| **Availability** | High-availability infrastructure (specific SLA not published) | — |
| **Cost** | Network fees charged to issuers/acquirers (not publicly disclosed) | — |
| **Market Share (US)** | 25.8% of card spending (2024) | Nilson Report |
| **Market Share (Global)** | ~17.6% of purchase volume | Nilson Report (2022) |

**Key Technical Details:**
- Mastercard Transaction Stream: new processing technology for real-time card payments
- First market: South Africa (real-time card payments)
- Contactless payments: >2/3 of in-person purchases on Mastercard network
- Tap on Phone: democratizing acceptance for merchants
- AI-powered cybersecurity for real-time fraud detection
- Partnership with ACI Worldwide for real-time processing standards

---

## 3. American Express

| Metric | Value | Source |
|--------|-------|--------|
| **Latency** | Sub-100ms (GTR optimized for low latency) | Amex Technology Blog |
| **Throughput** | Not explicitly published; $1.67T billed business (2025) | Amex FY2025 Results |
| **Availability** | 99.99%+ (zero-downtime migrations achieved) | Amex Technology Blog |
| **Cost** | Higher merchant fees (closed-loop model) | — |
| **Market Share (US)** | 11.1% of card spending (2024) | Nilson Report |
| **Market Share (Global)** | ~5.3% of purchase volume | Nilson Report (2022) |

**Key Technical Details:**
- Closed-loop network: card issuing + merchant acquiring + network
- Global Transaction Router (GTR): gateway for ISO8583 messages over long-lived TCP connections
- Migrated payments network twice with zero customer-impacting downtime
- Microservices-based payments processing platform
- 170M+ merchant locations worldwide (2025)
- 83.6M proprietary cards-in-force (2024); 62.8M third-party issued
- Kubernetes-based infrastructure with multi-region canary routing

---

## 4. Discover

| Metric | Value | Source |
|--------|-------|--------|
| **Latency** | Not explicitly published | — |
| **Throughput** | $634B across Discover Network, Diners Club, PULSE (2025) | Discover Global Network |
| **Availability** | Not explicitly published | — |
| **Cost** | Lower merchant fees | — |
| **Market Share (US)** | 2.0% of card spending (2024) | Nilson Report |
| **Market Share (Global)** | Included in "Others" (~5.3%) | Nilson Report (2022) |

**Key Technical Details:**
- Closed-loop network (now part of Capital One, acquired Feb 2025)
- Three brands: Discover Network, Diners Club International, PULSE
- Accepted in 185+ countries and territories
- $402.5B payment services transaction volume (2024, +10% YoY)
- Focus on scalability and interoperability within ecosystem

---

## 5. PayPal

| Metric | Value | Source |
|--------|-------|--------|
| **Latency (authorization)** | Median: 187ms; P95: 392ms; P99: 641ms | TheGadgetDigest (Q2 2024) |
| **Latency (P2P)** | Sub-12 seconds (Service 83908); median 9.7s | FrameAndFocal (2024) |
| **Throughput** | 1.2M transactions/hour at peak (Service 83908) | FrameAndFocal (2024) |
| **Availability** | 99.99% per AZ; 99.995% webhook uptime; 99.98% global uptime | Multiple sources |
| **Cost** | 2.99% + $0.49 standard; 3.49% + $0.49 branded; 4.99% intl; 3-4% FX spread | StackSelector (2025) |
| **Market Share** | Major digital wallet/processor (not a card network) | — |

**Key Technical Details:**
- 12,400+ microservices (up from 9,800 in 2021)
- Service 83908: next-gen P2P infrastructure with FedNow integration
- Real-time settlement with 14 participating financial institutions
- Zero-trust architecture (NIST SP 800-207 certified)
- ISO 20022 message formatting native support
- Webhook delivery: exponential backoff retry (max 5 attempts over 12 min)
- 36 production nodes across AWS and Google Cloud

---

## 6. Stripe

| Metric | Value | Source |
|--------|-------|--------|
| **Latency (p99)** | 89ms (Q3 2024); 82ms card-present (Black Friday 2024) | TrendDataAxis, Johal.in |
| **Latency (mean)** | 42ms | Johal.in (Q3 2024) |
| **Throughput (peak)** | 10,342,117 TPS (Black Friday 2024) | Johal.in |
| **Throughput (annual)** | 12.4B payment requests (Q3 2024) | TrendDataAxis |
| **Availability** | 99.999% (Black Friday 2024); 99.99% uptime | Johal.in, Finantrix |
| **Cost** | 2.9% + $0.30 standard; 2.7% + $0.05 in-person; +1.5% intl; +1% FX | StackSelector (2025) |
| **Market Share** | Dominant online payment processor for SaaS/e-commerce | — |

**Key Technical Details:**
- Stack: Go 1.26, Kafka 4.2, CockroachDB 24.2, Kubernetes 1.30, Envoy 1.30
- Multi-region active-active: 8 AWS regions, 23 availability zones
- 4,200 microservices generating 2.7TB operational metrics/hour
- 180+ SRE engineers
- gRPC 1.60 with protobuf (migrated from REST/JSON)
- HTTP/2 flow control windows tuned to 1MB for large payment payloads
- Go 1.24 PGO (profile-guided optimization) for 12% throughput gain
- Layered rate limiting: Envoy edge (10K req/merchant/sec), Kafka partitioning by merchant ID
- Cross-region settlement: 1.2s p99 (CockroachDB 24.2)
- Kafka tiered storage with S3 offload: 78% storage cost reduction

---

## 7. Square (Block, Inc.)

| Metric | Value | Source |
|--------|-------|--------|
| **Latency (p99)** | <287ms (Black Friday 2025) | Finantrix |
| **Throughput (peak)** | 47,000 TPS (Black Friday 2025) | Finantrix |
| **Throughput (annual)** | $228B processed (2024) | Wikipedia |
| **Availability** | 99.99% uptime SLA | Square Cloud |
| **Cost** | 2.6% + $0.10 in-person; 2.9% + $0.30 online | Multiple sources |
| **Market Share** | Major US POS player | — |

**Key Technical Details:**
- Cell-based architecture: 1,200+ processing cells, each operating independently
- Failure in one cell affects at most 0.08% of transaction volume
- 147 KPIs tracked in real-time
- Automated remediation for 82 common failure scenarios
- Offline payments: processed when reconnected (24-hour window)
- Square Checking: instant availability of funds
- 14-hour outage in September 2023 (notable incident)

---

## 8. Adyen

| Metric | Value | Source |
|--------|-------|--------|
| **Latency** | Not explicitly published; focuses on payment performance optimization | Adyen Index |
| **Throughput** | $43B over Black Friday/Cyber Monday weekend (2025) | Adyen (2025) |
| **Availability** | High availability; single platform with licensed infrastructure | Adyen |
| **Cost** | Interchange++ pricing model | — |
| **Market Share** | Major global payment processor | — |

**Key Technical Details:**
- Dutch payment company with acquiring bank status
- Single platform for online, mobile, and POS payments
- Licensed infrastructure in multiple jurisdictions
- Adyen Uplift: AI-optimization product suite (launched 2025)
- Record $43B processed over BFCM weekend 2025
- €1.996B revenue (2024); €925M net income (2024)
- Q3 2025: €598.4M net revenue (+20% YoY)

---

## 9. Worldpay

| Metric | Value | Source |
|--------|-------|--------|
| **Latency** | Webhook latency: 2-5 seconds average | SaaStr AI API Report |
| **Throughput** | Per-merchant rate limits: 100-500 TPS (depending on tier) | SaaStr AI API Report |
| **Availability** | Generally high; some incidents (Interlink, iDeal issues Sep 2026) | Worldpay Status Page |
| **Cost** | Custom pricing | — |
| **Market Share** | Major global payment processor | — |

**Key Technical Details:**
- API Grade: B (67/100) for AI agent readiness
- No rate-limit headers returned (RateLimit-Remaining, RateLimit-Reset)
- Does not support FedNow or RTP (real-time payments)
- Settlement: T+2 standard; next-day available (fee)
- 174+ countries, 250 currencies supported
- $340M invested 2023-2025 modernizing core processing platform
- Migrated from mainframe to hybrid cloud (Red Hat OpenShift + GCP)
- Unplanned downtime reduced from 3.7 hours/year to 26 minutes

---

## 10. Fiserv

| Metric | Value | Source |
|--------|-------|--------|
| **Latency** | Sub-100ms | MatrixBCG |
| **Throughput (peak)** | 25,000+ TPS | Fiserv corporate |
| **Throughput (annual)** | >16B transactions; $1.5T payments (2024) | MatrixBCG |
| **Availability** | 99.999%; >99.99% SLA; 24/7 uptime | MatrixBCG |
| **Cost** | Custom pricing for banks/enterprises | — |
| **Market Share** | Largest core banking processor; ~10,000 financial institutions | Fiserv corporate |

**Key Technical Details:**
- Processes 98 billion transactions (2024)
- Serves 20,000 financial institutions worldwide
- Clover platform: ~550,000 US endpoints (2025)
- MoneyPass surcharge-free ATM network: ~40,000 ATMs
- 35% of workloads moved to public cloud (2024)
- $1.2B R&D spend (2024, +8% YoY)
- $6.1B merchant revenue (FY2024, +6%)
- 98% retention in core processing
- Incident recovery time: <15 minutes (2024)
- Partnerships with Visa, Mastercard, Amex for transaction routing
- Reduced authorization latency by up to 18% (2024)

---

## Comparative Summary

### Latency Ranking (Fastest to Slowest)

| Rank | Network | Latency | Notes |
|------|--------|---------|-------|
| 1 | Fiserv | Sub-100ms | Core banking processing |
| 2 | Amex | Sub-100ms | GTR optimized for low latency |
| 3 | Stripe | 42ms mean, 82-89ms p99 | Go 1.26 + gRPC |
| 4 | PayPal | 187ms median, 641ms p99 | Authorization latency |
| 5 | Square | <287ms p99 | Black Friday peak |
| 6 | Visa | <1 second | Authorization |
| 7 | Mastercard | Milliseconds | Authorization |
| 8 | Worldpay | 2-5 seconds | Webhook latency |
| 9 | Adyen | Not published | — |
| 10 | Discover | Not published | — |

### Throughput Ranking (Peak TPS)

| Rank | Network | Peak TPS | Notes |
|------|--------|----------|-------|
| 1 | Stripe | 10,342,117 | Black Friday 2024 |
| 2 | Square | 47,000 | Black Friday 2025 |
| 3 | Fiserv | 25,000+ | Sustained peak |
| 4 | Visa | 83,000 msg/sec | Transaction messages |
| 5 | PayPal | ~333 TPS | 1.2M/hour |
| 6 | Worldpay | 100-500 TPS | Per-merchant limit |
| 7-10 | Others | Not published | — |

### Availability Ranking

| Rank | Network | Availability | Downtime/Year |
|------|--------|--------------|---------------|
| 1 | Visa | 99.9999% | <1 second/day |
| 2 | Stripe | 99.999% | ~5 minutes |
| 3 | Fiserv | 99.999% | ~5 minutes |
| 4 | Amex | 99.99%+ | ~52 minutes |
| 5 | PayPal | 99.99% | ~52 minutes |
| 6 | Square | 99.99% | ~52 minutes |
| 7-10 | Others | Not published | — |

### Cost Comparison (Online Card Transactions)

| Network | Standard Rate | International | FX Conversion |
|---------|--------------|---------------|---------------|
| Stripe | 2.9% + $0.30 | +1.5% | +1.0% |
| PayPal | 2.99% + $0.49 | +1.5% | 3-4% (hidden) |
| Square | 2.9% + $0.30 | — | — |
| Adyen | Interchange++ | Varies | Varies |
| Worldpay | Custom | Custom | Custom |

### Market Share (US Card Spending, 2024)

| Network | Share |
|---------|-------|
| Visa | 61.1% |
| Mastercard | 25.8% |
| American Express | 11.1% |
| Discover | 2.0% |

---

## Key Observations

1. **Latency leaders:** Stripe (42ms mean) and Fiserv/Amex (sub-100ms) lead in published latency metrics. Card networks (Visa, Mastercard) process authorizations in milliseconds but don't publish specific numbers.

2. **Throughput king:** Stripe's 10.3M TPS on Black Friday 2024 is the highest published figure, enabled by Go 1.26 + Kafka 4.2 + CockroachDB 24.2 stack.

3. **Availability champion:** Visa's "six nines" (99.9999%) is the gold standard, equating to less than 1 second of downtime per day.

4. **Cost winner:** Stripe generally offers lower fees than PayPal, especially for international transactions (transparent 1% FX vs. PayPal's hidden 3-4% spread).

5. **Architecture trends:**
   - Migration from REST/JSON to gRPC/protobuf (Stripe)
   - Cell-based architectures for fault isolation (Square)
   - Multi-region active-active deployments (Stripe, PayPal)
   - Real-time payment rails (Mastercard Transaction Stream, PayPal FedNow)
   - Zero-downtime migrations via canary routing (Amex)

6. **Market concentration:** Visa and Mastercard dominate US card spending (86.9% combined), while Stripe dominates online payment processing for SaaS/e-commerce.

---

## Sources

- Visa corporate website and VisaNet booklet (2025)
- Mastercard corporate website and press releases (2024-2025)
- American Express FY2025 Results and Technology Blog (2025-2026)
- Discover Global Network website (2025)
- PayPal technical infrastructure reports (2024)
- Stripe case studies and technical benchmarks (2024)
- Square/Block corporate releases and Wikipedia (2024-2025)
- Adyen Annual Report and Index Reports (2024-2025)
- Worldpay status page and API documentation (2024-2026)
- Fiserv corporate website and MatrixBCG analysis (2024)
- Nilson Report (2024-2025)
- Statista (2025)
- WalletHub (2026)
