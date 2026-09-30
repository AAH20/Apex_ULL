"""
Cross-Chain Arbitrage Application
==================================

Ultra-low-latency cross-chain arbitrage strategy engine with automatic
re-dispatch of failed strategies.

Architecture:
    - Multi-chain price feed aggregation
    - Real-time arbitrage opportunity detection
    - Strategy dispatch with failure recovery
    - Cross-chain order routing
    - Risk management and position tracking

ULL Principles Applied:
    - Lock-free ring buffers for price updates
    - Cache-friendly data structures (array-based, not pointer-chasing)
    - Pre-allocated buffers to avoid GC pauses
    - Deterministic execution paths
    - Minimal branching on hot path
"""

from .engine import ArbitrageEngine
from .models import (
    ChainId,
    Token,
    PriceUpdate,
    ArbitrageOpportunity,
    StrategyResult,
    DispatchConfig,
    OrderStatus,
    FailureReason,
    ChainState,
    Position,
)
from .detector import OpportunityDetector
from .dispatcher import StrategyDispatcher
from .risk import RiskManager
from .router import CrossChainRouter

__all__ = [
    "ArbitrageEngine",
    "ChainId",
    "Token",
    "PriceUpdate",
    "ArbitrageOpportunity",
    "StrategyResult",
    "DispatchConfig",
    "OpportunityDetector",
    "StrategyDispatcher",
    "RiskManager",
    "CrossChainRouter",
]

__version__ = "1.0.0"
