"""
STAC Benchmark Suite - Unified Runner

Runs all STAC benchmarks and produces a consolidated report with:
- Multi-dimensional scoring with grade classification
- Statistical analysis (confidence intervals, CV, skewness, kurtosis)
- Comparative analysis across benchmarks
- Regression detection against saved baselines
- Histogram data for visualization

Usage:
    python run_all.py              # Run all benchmarks
    python run_all.py --quick      # Quick mode (fewer iterations)
    python run_all.py --benchmark STAC-M1  # Run single benchmark
    python run_all.py --output results.json  # Save results to JSON
    python run_all.py --baseline-dir baselines/  # Compare against baselines
    python run_all.py --save-baseline  # Save current results as baselines
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from common.harness import get_environment_info
from common.regression import compare_to_baseline, load_baseline, save_baseline
from common.comparative import compare_benchmarks, generate_comparison_table


def run_all(quick: bool = False, single: str | None = None) -> dict:
    """Run all STAC benchmarks and return consolidated results."""
    iterations = 50_000 if quick else 500_000
    warmup = 5_000 if quick else 50_000

    results = {}

    benchmarks = {
        "STAC-M1": ("stac_m1_feed_handling.benchmark", "run_stac_m1"),
        "STAC-M2": ("stac_m2_messaging_middleware.benchmark", "run_stac_m2"),
        "STAC-M3": ("stac_m3_tick_analytics.benchmark", "run_stac_m3"),
        "STAC-A2": ("stac_a2_risk_computation.benchmark", "run_stac_a2"),
        "STAC-T0": ("stac_t0_network_io.benchmark", "run_stac_t0"),
        "STAC-T1": ("stac_t1_tick_to_trade.benchmark", "run_stac_t1"),
    }

    if single:
        if single not in benchmarks:
            print(f"Unknown benchmark: {single}")
            print(f"Available: {', '.join(benchmarks.keys())}")
            return {}
        benchmarks = {single: benchmarks[single]}

    print("=" * 70)
    print("STAC Benchmark Suite v2.0")
    print("=" * 70)
    print(f"Environment: {json.dumps(get_environment_info(), indent=2)}")
    print(f"Iterations: {iterations:,} per benchmark")
    print(f"Warmup: {warmup:,} per benchmark")
    print("=" * 70)
    print()

    for name, (module_name, func_name) in benchmarks.items():
        print(f"Running {name}...", end=" ", flush=True)
        t0 = time.time()

        try:
            module = importlib.import_module(module_name)
            run_fn = getattr(module, func_name)
            result = run_fn(iterations=iterations, warmup_iterations=warmup)
            results[name] = result.to_dict()

            elapsed = time.time() - t0
            print(f"done in {elapsed:.1f}s")
            print(f"  p50: {result.latency.p50_ns:,} ns")
            print(f"  p99: {result.latency.p99_ns:,} ns")
            print(f"  throughput: {result.throughput_ops_s:,.0f} ops/s")
            print(f"  jitter: {result.latency.jitter_ns:.1f} ns")
            print(f"  CV: {result.latency.cv:.3f}")
            if result.score_breakdown:
                sb = result.score_breakdown
                print(f"  score: {result.score:.4f} (grade: {sb.grade} - {sb.grade_label})")
                print(f"    latency: {sb.latency_score:.4f}, throughput: {sb.throughput_score:.4f}, "
                      f"jitter: {sb.jitter_score:.4f}")
                print(f"    tail: {sb.tail_latency_score:.4f}, consistency: {sb.consistency_score:.4f}")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"FAILED after {elapsed:.1f}s: {e}")
            import traceback
            traceback.print_exc()
            results[name] = {"error": str(e)}

        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Benchmark':<12} {'p50 (ns)':>12} {'p99 (ns)':>12} {'Throughput':>14} {'Score':>10} {'Grade':>6}")
    print("-" * 70)
    for name, data in results.items():
        if "error" in data:
            print(f"{name:<12} {'ERROR':>12}")
        else:
            lat = data["latency"]
            score = data.get("score", 0)
            grade = data.get("score_breakdown", {}).get("grade", "N/A") if data.get("score_breakdown") else "N/A"
            print(f"{name:<12} {lat['p50_ns']:>12,} {lat['p99_ns']:>12,} "
                  f"{data['throughput_ops_s']:>14,.0f} {score:>10.4f} {grade:>6}")
    print("=" * 70)

    print("No cross-workload score: these are unofficial synthetic examples, not STAC results.")


def main():
    parser = argparse.ArgumentParser(description="STAC Benchmark Suite")
    parser.add_argument("--quick", action="store_true", help="Quick mode (fewer iterations)")
    parser.add_argument("--benchmark", type=str, help="Run single benchmark (e.g., STAC-M1)")
    parser.add_argument("--output", type=str, help="Output JSON file for results")
    parser.add_argument("--baseline-dir", type=str, help="Directory containing baseline files for regression comparison")
    parser.add_argument("--save-baseline", action="store_true", help="Save current results as baselines")
    args = parser.parse_args()

    results = run_all(quick=args.quick, single=args.benchmark)
    if any("error" in result for result in results.values()):
        raise SystemExit("Synthetic benchmark failure; refusing a successful suite result")

    # Regression detection
    if args.baseline_dir and results:
        print("=" * 70)
        print("REGRESSION ANALYSIS")
        print("=" * 70)
        baseline_dir = Path(args.baseline_dir)
        for name, data in results.items():
            if "error" in data:
                continue
            baseline_path = baseline_dir / f"{name.lower().replace('-', '_')}.json"
            baseline = load_baseline(baseline_path)
            if baseline:
                # Reconstruct a minimal BenchmarkResult for comparison
                from common.harness import BenchmarkResult, LatencyStats
                lat_data = data["latency"]
                latency = LatencyStats(**{k: lat_data[k] for k in lat_data})
                result = BenchmarkResult(
                    name=name,
                    version=data.get("version", ""),
                    description=data.get("description", ""),
                    duration_s=data.get("duration_s", 0),
                    iterations=data.get("iterations", 0),
                    throughput_ops_s=data.get("throughput_ops_s", 0),
                    latency=latency,
                    score=data.get("score", 0),
                )
                report = compare_to_baseline(result, baseline)
                print(f"\n{name}: {report.overall_status.upper()}")
                print(f"  {report.summary}")
                for delta in report.deltas:
                    if delta.direction != "unchanged":
                        print(f"  {delta.metric_name}: {delta.percent_change:+.2f}% ({delta.direction}, {delta.severity})")
            else:
                print(f"\n{name}: No baseline found at {baseline_path}")
        print()

    # Save baselines
    if args.save_baseline and results:
        baseline_dir = Path("baselines")
        baseline_dir.mkdir(exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        for name, data in results.items():
            if "error" in data:
                continue
            from common.harness import BenchmarkResult, LatencyStats
            lat_data = data["latency"]
            latency = LatencyStats(**{k: lat_data[k] for k in lat_data})
            result = BenchmarkResult(
                name=name,
                version=data.get("version", ""),
                description=data.get("description", ""),
                duration_s=data.get("duration_s", 0),
                iterations=data.get("iterations", 0),
                throughput_ops_s=data.get("throughput_ops_s", 0),
                latency=latency,
                score=data.get("score", 0),
            )
            path = baseline_dir / f"{name.lower().replace('-', '_')}.json"
            save_baseline(result, path, timestamp)
            print(f"Saved baseline: {path}")
        print()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
