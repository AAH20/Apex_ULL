# ULL Security Evaluation Framework

Ultra-low-latency (ULL) infrastructure security overhead evaluation framework.
Each document covers measurement methodology, benchmark standards, and industry averages
for one security dimension.

## Dimensions

| # | Dimension | Document | Primary Concern |
|---|-----------|----------|-----------------|
| 1 | Encryption Overhead | [encryption-overhead.md](./encryption-overhead.md) | Data-in-transit & data-at-rest crypto latency |
| 2 | Authentication Overhead | [authentication-overhead.md](./authentication-overhead.md) | Identity verification latency per request |
| 3 | Authorization Overhead | [authorization-overhead.md](./authorization-overhead.md) | Policy decision latency per request |
| 4 | Audit Overhead | [audit-overhead.md](./audit-overhead.md) | Logging & audit trail generation latency |

## Evaluation Workflow

1. **Baseline** — Measure raw system latency without security controls
2. **Isolated** — Measure each security dimension in isolation
3. **Stacked** — Measure cumulative overhead with all controls active
4. **Compare** — Compare against industry averages and ULL budget targets

## ULL Latency Budget Reference

| Tier | Total Security Budget | Target p99 |
|------|----------------------|------------|
| Tier 0 (HFT / Market Data) | ≤ 50 µs | ≤ 10 µs |
| Tier 1 (Real-time Trading) | ≤ 200 µs | ≤ 50 µs |
| Tier 2 (Interactive / API) | ≤ 1 ms | ≤ 200 µs |
| Tier 3 (Standard Web) | ≤ 5 ms | ≤ 1 ms |

## Key Principles

- **Measure at the p99/p999 tail**, not the mean — ULL systems are tail-latency sensitive
- **Isolate variables** — test each security control independently before stacking
- **Use hardware-accelerated paths** where available (AES-NI, QAT, etc.)
- **Account for cache effects** — cold vs. warm key/token caches differ by orders of magnitude
- **Document the threat model** — overhead targets vary by required security guarantees
