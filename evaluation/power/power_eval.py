"""
ULL Power Evaluation Framework
===============================

Standardized power evaluation for ultra-low-latency infrastructure.

Metrics:
  - Watts per Operation (W/op)
  - Watts per Message (W/msg)
  - Energy Efficiency (ops/J, msg/J)
  - Carbon Footprint (gCO₂e/op, gCO₂e/msg)

Usage:
    from power_eval import PowerEvaluator

    eval = PowerEvaluator()
    result = eval.watts_per_operation(power_watts=40, operations_per_second=150_000)
    print(f"W/op: {result['watts_per_operation']:.2e} W/op")
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Carbon intensity by region (gCO₂e/kWh) — IEA 2024 / EPA 2024
CARBON_INTENSITY: dict[str, float] = {
    "norway": 20,
    "france": 50,
    "quebec": 30,
    "california": 200,
    "new_york": 250,
    "texas": 400,
    "singapore": 450,
    "hong_kong": 500,
    "japan": 450,
    "germany": 350,
    "india": 600,
    "china": 550,
    "global_average": 450,
}

# PUE by facility type
PUE_BY_FACILITY: dict[str, float] = {
    "hyperscale": 1.15,
    "colocation": 1.45,
    "enterprise": 1.7,
    "edge": 1.1,
    "hft_colocation": 1.3,
}

# Unit prefixes
PREFIXES: dict[str, float] = {
    "p": 1e-12,   # pico
    "n": 1e-9,    # nano
    "u": 1e-6,    # micro
    "m": 1e-3,    # milli
    "": 1.0,      # base
    "k": 1e3,     # kilo
    "M": 1e6,     # mega
    "G": 1e9,     # giga
    "T": 1e12,    # tera
    "P": 1e15,    # peta
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PowerResult:
    """Result of a power evaluation."""
    metric: str
    value: float
    unit: str
    power_watts: float
    throughput: float
    throughput_unit: str
    pue: float
    carbon_intensity: float
    carbon_per_unit: float
    carbon_unit: str
    energy_per_unit: float
    energy_unit: str
    efficiency: float
    efficiency_unit: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class PlatformProfile:
    """Hardware platform power/performance profile."""
    name: str
    power_watts: float
    throughput: float
    throughput_unit: str  # "ops/s", "msg/s", "pkt/s", "FLOP/s"
    process_node: str = ""
    category: str = ""  # "FPGA", "CPU", "GPU", "NIC", "Switch"
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

class PowerEvaluator:
    """Evaluate power consumption and carbon footprint of ULL infrastructure."""

    def __init__(self, pue: float = 1.3, carbon_intensity: float = 450.0):
        """
        Initialize evaluator.

        Args:
            pue: Power Usage Effectiveness (1.0 = ideal, 2.0 = poor)
            carbon_intensity: Grid carbon intensity in gCO₂e/kWh
        """
        self.pue = pue
        self.carbon_intensity = carbon_intensity

    def watts_per_operation(
        self,
        power_watts: float,
        operations_per_second: float,
        pue: Optional[float] = None,
        carbon_intensity: Optional[float] = None,
    ) -> PowerResult:
        """
        Calculate watts per operation.

        Args:
            power_watts: Device/board power draw in watts
            operations_per_second: Operations per second
            pue: PUE override (uses instance default if None)
            carbon_intensity: Carbon intensity override (gCO₂e/kWh)

        Returns:
            PowerResult with all metrics
        """
        pue = pue if pue is not None else self.pue
        ci = carbon_intensity if carbon_intensity is not None else self.carbon_intensity

        total_power = power_watts * pue
        w_per_op = total_power / operations_per_second
        energy_per_op = w_per_op  # J/op = W / (ops/s)
        efficiency = operations_per_second / total_power  # ops/J
        carbon_per_op = self._carbon_per_unit(energy_per_op, ci)

        return PowerResult(
            metric="watts_per_operation",
            value=w_per_op,
            unit="W/op",
            power_watts=total_power,
            throughput=operations_per_second,
            throughput_unit="ops/s",
            pue=pue,
            carbon_intensity=ci,
            carbon_per_unit=carbon_per_op,
            carbon_unit="gCO₂e/op",
            energy_per_unit=energy_per_op,
            energy_unit="J/op",
            efficiency=efficiency,
            efficiency_unit="ops/J",
        )

    def watts_per_message(
        self,
        power_watts: float,
        messages_per_second: float,
        pue: Optional[float] = None,
        carbon_intensity: Optional[float] = None,
    ) -> PowerResult:
        """
        Calculate watts per message.

        Args:
            power_watts: Device/board power draw in watts
            messages_per_second: Messages per second
            pue: PUE override
            carbon_intensity: Carbon intensity override (gCO₂e/kWh)

        Returns:
            PowerResult with all metrics
        """
        pue = pue if pue is not None else self.pue
        ci = carbon_intensity if carbon_intensity is not None else self.carbon_intensity

        total_power = power_watts * pue
        w_per_msg = total_power / messages_per_second
        energy_per_msg = w_per_msg  # J/msg = W / (msg/s)
        efficiency = messages_per_second / total_power  # msg/J
        carbon_per_msg = self._carbon_per_unit(energy_per_msg, ci)

        return PowerResult(
            metric="watts_per_message",
            value=w_per_msg,
            unit="W/msg",
            power_watts=total_power,
            throughput=messages_per_second,
            throughput_unit="msg/s",
            pue=pue,
            carbon_intensity=ci,
            carbon_per_unit=carbon_per_msg,
            carbon_unit="gCO₂e/msg",
            energy_per_unit=energy_per_msg,
            energy_unit="J/msg",
            efficiency=efficiency,
            efficiency_unit="msg/J",
        )

    def energy_efficiency(
        self,
        power_watts: float,
        throughput: float,
        throughput_unit: str = "ops/s",
        pue: Optional[float] = None,
    ) -> PowerResult:
        """
        Calculate energy efficiency (throughput per joule).

        Args:
            power_watts: Device power draw in watts
            throughput: Throughput value
            throughput_unit: Unit of throughput
            pue: PUE override

        Returns:
            PowerResult with efficiency metrics
        """
        pue = pue if pue is not None else self.pue
        total_power = power_watts * pue
        efficiency = throughput / total_power
        energy_per_unit = total_power / throughput

        return PowerResult(
            metric="energy_efficiency",
            value=efficiency,
            unit=f"{throughput_unit.split('/')[0]}/J",
            power_watts=total_power,
            throughput=throughput,
            throughput_unit=throughput_unit,
            pue=pue,
            carbon_intensity=self.carbon_intensity,
            carbon_per_unit=self._carbon_per_unit(energy_per_unit, self.carbon_intensity),
            carbon_unit=f"gCO₂e/{throughput_unit.split('/')[0]}",
            energy_per_unit=energy_per_unit,
            energy_unit=f"J/{throughput_unit.split('/')[0]}",
            efficiency=efficiency,
            efficiency_unit=f"{throughput_unit.split('/')[0]}/J",
        )

    def carbon_footprint(
        self,
        power_watts: float,
        throughput: float,
        throughput_unit: str = "ops/s",
        pue: Optional[float] = None,
        carbon_intensity: Optional[float] = None,
    ) -> PowerResult:
        """
        Calculate carbon footprint per unit of work.

        Args:
            power_watts: Device power draw in watts
            throughput: Throughput value
            throughput_unit: Unit of throughput
            pue: PUE override
            carbon_intensity: Carbon intensity override (gCO₂e/kWh)

        Returns:
            PowerResult with carbon metrics
        """
        pue = pue if pue is not None else self.pue
        ci = carbon_intensity if carbon_intensity is not None else self.carbon_intensity

        total_power = power_watts * pue
        energy_per_unit = total_power / throughput  # J per unit
        carbon_per_unit = self._carbon_per_unit(energy_per_unit, ci)
        efficiency = throughput / total_power

        return PowerResult(
            metric="carbon_footprint",
            value=carbon_per_unit,
            unit=f"gCO₂e/{throughput_unit.split('/')[0]}",
            power_watts=total_power,
            throughput=throughput,
            throughput_unit=throughput_unit,
            pue=pue,
            carbon_intensity=ci,
            carbon_per_unit=carbon_per_unit,
            carbon_unit=f"gCO₂e/{throughput_unit.split('/')[0]}",
            energy_per_unit=energy_per_unit,
            energy_unit=f"J/{throughput_unit.split('/')[0]}",
            efficiency=efficiency,
            efficiency_unit=f"{throughput_unit.split('/')[0]}/J",
        )

    def compare_platforms(
        self,
        platforms: list[dict],
        pue: Optional[float] = None,
        carbon_intensity: Optional[float] = None,
    ) -> list[PowerResult]:
        """
        Compare multiple platforms on energy efficiency.

        Args:
            platforms: List of dicts with keys: name, power, ops_s (or throughput)
            pue: PUE override
            carbon_intensity: Carbon intensity override

        Returns:
            List of PowerResult sorted by efficiency (descending)
        """
        pue = pue if pue is not None else self.pue
        ci = carbon_intensity if carbon_intensity is not None else self.carbon_intensity

        results = []
        for p in platforms:
            power = p["power"]
            throughput = p.get("ops_s", p.get("throughput", 0))
            unit = p.get("unit", "ops/s")

            result = self.energy_efficiency(power, throughput, unit, pue)
            result.metadata = {
                "name": p.get("name", "unknown"),
                "category": p.get("category", ""),
                "process_node": p.get("process_node", ""),
            }
            results.append(result)

        results.sort(key=lambda r: r.efficiency, reverse=True)
        return results

    def print_comparison(self, results: list[PowerResult]) -> None:
        """Print a formatted comparison table."""
        print(f"{'Platform':<25} {'Power(W)':<10} {'Throughput':<15} {'Efficiency':<15} {'Carbon/unit':<15}")
        print("-" * 80)
        for r in results:
            name = r.metadata.get("name", "unknown")
            power = r.power_watts
            throughput = f"{self._fmt(r.throughput)} {r.throughput_unit}"
            efficiency = f"{self._fmt(r.efficiency)} {r.efficiency_unit}"
            carbon = f"{self._fmt(r.carbon_per_unit)} {r.carbon_unit}"
            print(f"{name:<25} {power:<10.1f} {throughput:<15} {efficiency:<15} {carbon:<15}")

    def _carbon_per_unit(self, energy_joules: float, carbon_intensity: float) -> float:
        """
        Convert energy in joules to carbon in gCO₂e.

        Formula: gCO₂e = J × (gCO₂e/kWh) / 3,600,000
        (1 kWh = 3,600,000 J)
        """
        return energy_joules * carbon_intensity / 3_600_000

    @staticmethod
    def _fmt(value: float) -> str:
        """Format a number with appropriate SI prefix."""
        if value == 0:
            return "0"
        abs_val = abs(value)
        if abs_val >= 1e15:
            return f"{value/1e15:.2f}P"
        elif abs_val >= 1e12:
            return f"{value/1e12:.2f}T"
        elif abs_val >= 1e9:
            return f"{value/1e9:.2f}G"
        elif abs_val >= 1e6:
            return f"{value/1e6:.2f}M"
        elif abs_val >= 1e3:
            return f"{value/1e3:.2f}k"
        elif abs_val >= 1:
            return f"{value:.2f}"
        elif abs_val >= 1e-3:
            return f"{value*1e3:.2f}m"
        elif abs_val >= 1e-6:
            return f"{value*1e6:.2f}µ"
        elif abs_val >= 1e-9:
            return f"{value*1e9:.2f}n"
        else:
            return f"{value*1e12:.2f}p"


# ---------------------------------------------------------------------------
# Pre-built platform profiles (from research data)
# ---------------------------------------------------------------------------

FPGA_PROFILES: list[PlatformProfile] = [
    PlatformProfile("AMD Versal AI Edge", 40, 150_000, "ops/s", "7nm", "FPGA", "AMD"),
    PlatformProfile("Intel Agilex 7", 60, 2_000_000_000, "ops/s", "10nm", "FPGA", "Intel"),
    PlatformProfile("Lattice Nexus", 2, 100_000_000, "ops/s", "28nm", "FPGA", "Lattice"),
    PlatformProfile("Microchip PolarFire", 3.5, 50_000_000, "ops/s", "28nm", "FPGA", "Microchip"),
    PlatformProfile("Achronix Speedster7t", 100, 61_000_000_000, "ops/s", "7nm", "FPGA", "Achronix"),
]

NETWORK_PROFILES: list[PlatformProfile] = [
    PlatformProfile("P4 Switch (64-port)", 270, 4_800_000_000, "pkt/s", "", "Switch", "Intel"),
    PlatformProfile("InfiniBand NDR Switch", 150, 330_000_000, "msg/s", "", "Switch", "NVIDIA"),
    PlatformProfile("100GbE NIC (DPDK)", 25, 100_000_000, "pkt/s", "", "NIC", "Generic"),
    PlatformProfile("ConnectX-7 RoCE", 30, 370_000_000, "msg/s", "", "NIC", "NVIDIA"),
    PlatformProfile("BlueField-3 DPU", 100, 80_000_000, "pkt/s", "", "DPU", "NVIDIA"),
]

CPU_GPU_PROFILES: list[PlatformProfile] = [
    PlatformProfile("Intel Xeon 8480+", 350, 500_000_000_000, "ops/s", "10nm", "CPU", "Intel"),
    PlatformProfile("AMD EPYC 9654", 360, 600_000_000_000, "ops/s", "5nm", "CPU", "AMD"),
    PlatformProfile("NVIDIA H100 SXM", 700, 1_000_000_000_000_000, "FLOP/s", "4nm", "GPU", "NVIDIA"),
    PlatformProfile("NVIDIA L40S", 300, 360_000_000_000_000, "FLOP/s", "5nm", "GPU", "NVIDIA"),
]


# ---------------------------------------------------------------------------
# CLI / Demo
# ---------------------------------------------------------------------------

def main():
    """Run demonstration of the power evaluation framework."""
    print("=" * 80)
    print("ULL Power Evaluation Framework — Demo")
    print("=" * 80)

    eval = PowerEvaluator(pue=1.3, carbon_intensity=450)

    # Example 1: FPGA tick-to-trade
    print("\n--- Example 1: FPGA Tick-to-Trade (HFT) ---")
    result = eval.watts_per_operation(
        power_watts=40,
        operations_per_second=150_000,
        pue=1.3,
        carbon_intensity=450,
    )
    print(f"  Power (device):     40 W")
    print(f"  Power (with PUE):   {result.power_watts:.1f} W")
    print(f"  Throughput:         150,000 ops/s")
    print(f"  Watts per op:       {eval._fmt(result.value)} W/op")
    print(f"  Energy per op:      {eval._fmt(result.energy_per_unit)} J/op")
    print(f"  Efficiency:         {eval._fmt(result.efficiency)} ops/J")
    print(f"  Carbon per op:      {eval._fmt(result.carbon_per_unit)} gCO₂e/op")

    # Example 2: DPDK packet processing
    print("\n--- Example 2: DPDK Packet Processing ---")
    result = eval.watts_per_message(
        power_watts=25,
        messages_per_second=100_000_000,
        pue=1.15,
        carbon_intensity=200,
    )
    print(f"  Power (device):     25 W")
    print(f"  Power (with PUE):   {result.power_watts:.1f} W")
    print(f"  Throughput:         100M pkt/s")
    print(f"  Watts per pkt:      {eval._fmt(result.value)} W/pkt")
    print(f"  Energy per pkt:     {eval._fmt(result.energy_per_unit)} J/pkt")
    print(f"  Efficiency:         {eval._fmt(result.efficiency)} pkt/J")
    print(f"  Carbon per pkt:     {eval._fmt(result.carbon_per_unit)} gCO₂e/pkt")

    # Example 3: AI inference
    print("\n--- Example 3: AI Inference (GPU) ---")
    result = eval.energy_efficiency(
        power_watts=300,
        throughput=360_000_000_000_000,
        throughput_unit="FLOP/s",
        pue=1.15,
    )
    print(f"  Power (device):     300 W")
    print(f"  Power (with PUE):   {result.power_watts:.1f} W")
    print(f"  Throughput:         360T FLOP/s")
    print(f"  Efficiency:         {eval._fmt(result.efficiency)} FLOP/J")
    print(f"  Energy per FLOP:    {eval._fmt(result.energy_per_unit)} J/FLOP")
    print(f"  Carbon per FLOP:    {eval._fmt(result.carbon_per_unit)} gCO₂e/FLOP")

    # Platform comparison
    print("\n--- Platform Comparison: Energy Efficiency ---")
    platforms = [
        {"name": "Lattice Nexus FPGA", "power": 2, "ops_s": 100_000_000, "unit": "ops/s", "category": "FPGA"},
        {"name": "Intel Agilex 7 FPGA", "power": 60, "ops_s": 2_000_000_000, "unit": "ops/s", "category": "FPGA"},
        {"name": "AMD Versal AI Edge", "power": 40, "ops_s": 150_000, "unit": "ops/s", "category": "FPGA"},
        {"name": "Microchip PolarFire", "power": 3.5, "ops_s": 50_000_000, "unit": "ops/s", "category": "FPGA"},
        {"name": "Intel Xeon 8480+", "power": 350, "ops_s": 500_000_000_000, "unit": "ops/s", "category": "CPU"},
        {"name": "NVIDIA H100", "power": 700, "ops_s": 1_000_000_000_000_000, "unit": "FLOP/s", "category": "GPU"},
    ]
    results = eval.compare_platforms(platforms, pue=1.3, carbon_intensity=450)
    eval.print_comparison(results)

    # Carbon footprint comparison
    print("\n--- Carbon Footprint by Region (same workload) ---")
    workload = {"power": 40, "throughput": 150_000, "unit": "ops/s"}
    regions = ["norway", "france", "california", "texas", "singapore", "india"]
    print(f"{'Region':<15} {'gCO₂e/kWh':<12} {'gCO₂e/op':<15} {'Relative':<10}")
    print("-" * 52)
    baseline = None
    for region in regions:
        ci = CARBON_INTENSITY[region]
        result = eval.carbon_footprint(
            power_watts=workload["power"],
            throughput=workload["throughput"],
            throughput_unit=workload["unit"],
            pue=1.3,
            carbon_intensity=ci,
        )
        if baseline is None:
            baseline = result.carbon_per_unit
        relative = result.carbon_per_unit / baseline
        print(f"{region:<15} {ci:<12.0f} {eval._fmt(result.carbon_per_unit):<15} {relative:<10.2f}x")

    print("\n" + "=" * 80)
    print("Demo complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
