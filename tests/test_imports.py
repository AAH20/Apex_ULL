"""Apex_ULL test suite."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_import_kernels():
    """Verify kernels package is importable."""
    import kernels
    assert kernels is not None


def test_import_scheduling():
    """Verify scheduling subpackage is importable."""
    from kernels.scheduling import jssp
    assert hasattr(jssp, "JSSPSolver")
    assert hasattr(jssp, "JSSPInstance")


def test_import_evaluation():
    """Verify evaluation package is importable."""
    import evaluation
    assert evaluation is not None


def test_import_benchmarks():
    """Verify benchmarks package is importable."""
    import benchmarks
    assert benchmarks is not None