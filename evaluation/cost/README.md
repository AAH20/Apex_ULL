# ULL Cost Evaluation Framework

Cost evaluation framework for ultra-low latency infrastructure.

## Files

| File | Description |
|------|-------------|
| `cost-evaluation-framework.md` | Complete framework document with formulas, benchmarks, and methodology |
| `cost_calculator.py` | Python calculator implementing all cost metrics with example deployments |
| `README.md` | This file |

## Quick Start

```bash
# Run the example calculator
python cost_calculator.py
```

## Metrics Covered

| Metric | Description | Unit |
|--------|-------------|------|
| **CPμs** | Cost per microsecond of latency reduction | $/μs |
| **CPT** | Cost per trade executed | $/trade |
| **CPM** | Cost per message processed | $/message |
| **TCO** | Total cost of ownership (5-year) | $ |
| **ROI** | Return on investment | % |

## Framework Structure

```
evaluation/cost/
├── cost-evaluation-framework.md   # Main document
├── cost_calculator.py             # Python calculator
└── README.md                      # This file
```

## Usage

Import the calculator and create your own model:

```python
from cost_calculator import ULLCostModel

model = ULLCostModel(
    baseline_latency_us=50.0,
    achieved_latency_us=1.0,
    annual_trades=100_000_000,
    annual_messages=1_000_000_000,
    revenue_with_ull=10_000_000,
    revenue_without_ull=5_000_000,
)

model.add_component("FPGA feed handlers", qty=4, unit_cost=10000, annual_opex=500)
model.add_component("100GbE NICs", qty=8, unit_cost=5000, annual_opex=300)

print(model.report())
```

## Benchmarks

See the main document for industry averages across:
- Retail brokerage
- Professional trading
- HFT firms
- Elite HFT (Citadel, Jump scale)
