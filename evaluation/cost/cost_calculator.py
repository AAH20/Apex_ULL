#!/usr/bin/env python3
"""
ULL Cost Evaluation Calculator
Implements the formulas from the cost evaluation framework.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class InfrastructureInventory:
    """Hardware and software inventory with costs."""
    component: str
    quantity: int
    unit_cost: float
    annual_opex_per_unit: float
    lifespan_years: float = 5.0

    @property
    def total_capex(self) -> float:
        return self.quantity * self.unit_cost

    @property
    def annual_opex(self) -> float:
        return self.quantity * self.annual_opex_per_unit

    @property
    def annualized_capex(self) -> float:
        return self.total_capex / self.lifespan_years


@dataclass
class ULLCostModel:
    """Complete ULL cost evaluation model."""

    # Infrastructure
    inventory: list[InfrastructureInventory] = field(default_factory=list)

    # Performance
    baseline_latency_us: float = 50.0
    achieved_latency_us: float = 1.0
    annual_trades: int = 100_000_000
    annual_messages: int = 1_000_000_000

    # Revenue
    revenue_with_ull: float = 0.0
    revenue_without_ull: float = 0.0

    # Risk
    downtime_probability: float = 0.005  # Annual probability of one incident (Bernoulli model).
    mean_downtime_hours_per_incident: float = 2.0
    cost_per_hour_downtime: float = 50_000
    obsolescence_factor: float = 0.3  # 30% of CapEx

    def add_component(self, component: str, qty: int, unit_cost: float,
                      annual_opex: float, lifespan: float = 5.0):
        """Add an infrastructure component."""
        self.inventory.append(InfrastructureInventory(
            component=component,
            quantity=qty,
            unit_cost=unit_cost,
            annual_opex_per_unit=annual_opex,
            lifespan_years=lifespan
        ))

    @property
    def total_capex(self) -> float:
        return sum(item.total_capex for item in self.inventory)

    @property
    def annual_opex(self) -> float:
        return sum(item.annual_opex for item in self.inventory)

    @property
    def annualized_capex(self) -> float:
        return sum(item.annualized_capex for item in self.inventory)

    @property
    def total_annual_cost(self) -> float:
        return self.annualized_capex + self.annual_opex

    @property
    def latency_improvement_us(self) -> float:
        return self.baseline_latency_us - self.achieved_latency_us

    @property
    def cp_us(self) -> float:
        """Cost per microsecond of latency reduction."""
        if self.latency_improvement_us <= 0:
            return float('inf')
        return self.total_annual_cost / self.latency_improvement_us

    @property
    def cpt(self) -> float:
        """Cost per trade."""
        if self.annual_trades <= 0:
            return float('inf')
        return self.total_annual_cost / self.annual_trades

    @property
    def cpm(self) -> float:
        """Cost per message."""
        if self.annual_messages <= 0:
            return float('inf')
        return self.total_annual_cost / self.annual_messages

    @property
    def risk_cost(self) -> float:
        """Annual risk cost."""
        downtime_cost = self.downtime_probability * self.mean_downtime_hours_per_incident * self.cost_per_hour_downtime
        obsolescence_cost = self.obsolescence_factor * self.total_capex / 5
        return downtime_cost + obsolescence_cost

    @property
    def five_year_tco(self) -> float:
        """5-year total cost of ownership."""
        return self.total_capex + 5 * self.annual_opex + 5 * self.risk_cost

    @property
    def annual_revenue_uplift(self) -> float:
        """Annual revenue attributable to ULL."""
        return self.revenue_with_ull - self.revenue_without_ull

    @property
    def roi_5yr(self) -> float:
        """5-year ROI percentage."""
        if self.five_year_tco <= 0:
            return 0.0
        return (5 * self.annual_revenue_uplift - self.five_year_tco) / self.five_year_tco * 100

    @property
    def payback_years(self) -> float:
        """Payback period in years."""
        annual_net_cashflow = self.annual_revenue_uplift - self.annual_opex - self.risk_cost
        if annual_net_cashflow <= 0:
            return float('inf')
        return self.total_capex / annual_net_cashflow

    def report(self) -> str:
        """Generate a formatted cost report."""
        lines = [
            "=" * 60,
            "  ULL COST EVALUATION REPORT",
            "=" * 60,
            "",
            "INFRASTRUCTURE INVENTORY",
            "-" * 40,
        ]
        for item in self.inventory:
            lines.append(
                f"  {item.component:30s}  Qty={item.quantity:3d}  "
                f"CapEx=${item.total_capex:>12,.0f}  "
                f"OpEx=${item.annual_opex:>10,.0f}/yr"
            )
        lines.extend([
            "-" * 40,
            f"  {'TOTAL':30s}       "
            f"CapEx=${self.total_capex:>12,.0f}  "
            f"OpEx=${self.annual_opex:>10,.0f}/yr",
            "",
            "PERFORMANCE METRICS",
            "-" * 40,
            f"  Baseline latency:     {self.baseline_latency_us:>10.1f} μs",
            f"  Achieved latency:     {self.achieved_latency_us:>10.1f} μs",
            f"  Latency improvement:  {self.latency_improvement_us:>10.1f} μs",
            f"  Annual trades:        {self.annual_trades:>15,}",
            f"  Annual messages:      {self.annual_messages:>15,}",
            "",
            "COST METRICS",
            "-" * 40,
            f"  Cost per μs (CPμs):   ${self.cp_us:>12,.2f}",
            f"  Cost per trade (CPT): ${self.cpt:>12,.6f}",
            f"  Cost per msg (CPM):   ${self.cpm:>12,.8f}",
            "",
            "TOTAL COST OF OWNERSHIP",
            "-" * 40,
            f"  Annualized CapEx:     ${self.annualized_capex:>12,.0f}",
            f"  Annual OpEx:          ${self.annual_opex:>12,.0f}",
            f"  Annual risk cost:     ${self.risk_cost:>12,.0f}",
            f"  5-Year TCO:           ${self.five_year_tco:>12,.0f}",
            "",
            "RETURN ON INVESTMENT",
            "-" * 40,
            f"  Annual revenue uplift: ${self.annual_revenue_uplift:>12,.0f}",
            f"  5-Year ROI:            {self.roi_5yr:>10.1f}%",
            f"  Payback period:        {self.payback_years:>10.1f} years",
            "=" * 60,
        ])
        return "\n".join(lines)


def example_small_prop():
    """Example: Small proprietary trading shop."""
    model = ULLCostModel(
        baseline_latency_us=50.0,
        achieved_latency_us=5.0,
        annual_trades=50_000_000,
        annual_messages=500_000_000,
        revenue_with_ull=2_000_000,
        revenue_without_ull=1_200_000,
    )
    model.add_component("FPGA feed handlers", 2, 8000, 500, 5)
    model.add_component("100GbE NICs", 4, 5000, 300, 4)
    model.add_component("Servers", 2, 20000, 1500, 4)
    model.add_component("Co-location (racks)", 2, 0, 24000, 1)
    model.add_component("Software licenses", 1, 50000, 10000, 3)
    return model


def example_mid_tier_hft():
    """Example: Mid-tier HFT firm."""
    model = ULLCostModel(
        baseline_latency_us=50.0,
        achieved_latency_us=1.0,
        annual_trades=500_000_000,
        annual_messages=10_000_000_000,
        revenue_with_ull=50_000_000,
        revenue_without_ull=20_000_000,
    )
    model.add_component("FPGA feed handlers", 8, 12000, 800, 5)
    model.add_component("100GbE NICs", 16, 6000, 400, 4)
    model.add_component("P4 switches", 4, 30000, 2000, 5)
    model.add_component("Servers", 8, 25000, 2000, 4)
    model.add_component("Microwave links", 2, 0, 2_000_000, 1)
    model.add_component("Co-location (racks)", 8, 0, 36000, 1)
    model.add_component("Software licenses", 1, 200000, 50000, 3)
    return model


def example_elite_hft():
    """Example: Elite HFT firm (Citadel/Jump scale)."""
    model = ULLCostModel(
        baseline_latency_us=50.0,
        achieved_latency_us=0.5,
        annual_trades=5_000_000_000,
        annual_messages=100_000_000_000,
        revenue_with_ull=500_000_000,
        revenue_without_ull=150_000_000,
    )
    model.add_component("FPGA feed handlers", 32, 15000, 1000, 5)
    model.add_component("100GbE NICs", 64, 8000, 500, 4)
    model.add_component("P4 switches", 16, 40000, 3000, 5)
    model.add_component("Servers", 32, 30000, 2500, 4)
    model.add_component("Microwave links", 8, 0, 5_000_000, 1)
    model.add_component("Co-location (racks)", 32, 0, 48000, 1)
    model.add_component("Software licenses", 1, 500000, 150000, 3)
    return model


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  EXAMPLE 1: Small Proprietary Trading Shop")
    print("=" * 60)
    print(example_small_prop().report())

    print("\n" + "=" * 60)
    print("  EXAMPLE 2: Mid-Tier HFT Firm")
    print("=" * 60)
    print(example_mid_tier_hft().report())

    print("\n" + "=" * 60)
    print("  EXAMPLE 3: Elite HFT Firm")
    print("=" * 60)
    print(example_elite_hft().report())
