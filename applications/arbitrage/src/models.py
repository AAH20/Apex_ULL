"""
Data Models for Cross-Chain Arbitrage
======================================

Core data structures optimized for ultra-low-latency processing.
All structures use __slots__ for memory efficiency and cache locality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional
import time


class ChainId(IntEnum):
    """Supported blockchain networks."""
    ETHEREUM = 1
    BSC = 56
    POLYGON = 137
    ARBITRUM = 42161
    OPTIMISM = 10
    AVALANCHE = 43114
    BASE = 8453
    SOLANA = 900  # Non-EVM, special handling


class OrderStatus(IntEnum):
    """Strategy execution status."""
    PENDING = 0
    DISPATCHED = 1
    EXECUTING = 2
    COMPLETED = 3
    FAILED = 4
    RETRYING = 5
    EXPIRED = 6


class FailureReason(IntEnum):
    """Reasons for strategy failure."""
    NONE = 0
    PRICE_MOVED = 1
    INSUFFICIENT_LIQUIDITY = 2
    GAS_TOO_HIGH = 3
    SLIPPAGE_EXCEEDED = 4
    BRIDGE_TIMEOUT = 5
    SMART_CONTRACT_REVERT = 6
    NETWORK_ERROR = 7
    RISK_LIMIT_HIT = 8
    UNKNOWN = 99


@dataclass
class Token:
    """Token definition on a specific chain."""
    address: str
    symbol: str
    decimals: int
    chain_id: ChainId
    # Pre-computed for hot path
    is_stable: bool = False
    is_wrapped: bool = False


@dataclass
class PriceUpdate:
    """Atomic price update from a DEX on a specific chain."""
    token_in: Token
    token_out: Token
    price: int  # Fixed-point with 18 decimals
    liquidity: int  # Available liquidity in wei
    timestamp_ns: int
    dex_id: str  # e.g., "uniswap_v3", "sushiswap", "pancakeswap"
    block_number: int
    # Pre-computed for fast comparison
    is_valid: bool = True


@dataclass
class ArbitrageOpportunity:
    """Detected cross-chain arbitrage opportunity."""
    id: int
    buy_chain: ChainId
    sell_chain: ChainId
    token: Token  # Token to bridge
    buy_price: int  # Price on buy chain (fixed-point)
    sell_price: int  # Price on sell chain (fixed-point)
    spread_bps: int  # Spread in basis points
    estimated_profit: int  # Estimated profit in wei
    confidence: float  # 0.0 to 1.0
    detected_at_ns: int
    expires_at_ns: int
    # Route information
    buy_dex: str
    sell_dex: str
    bridge_route: Optional[str] = None
    # Execution tracking
    status: OrderStatus = OrderStatus.PENDING
    attempt_count: int = 0
    last_error: FailureReason = FailureReason.NONE


@dataclass
class StrategyResult:
    """Result of a strategy execution attempt."""
    opportunity_id: int
    success: bool
    status: OrderStatus
    failure_reason: FailureReason
    execution_time_ns: int
    actual_profit: int = 0
    tx_hash: Optional[str] = None
    gas_used: int = 0
    gas_cost: int = 0
    # Re-dispatch info
    should_retry: bool = False
    retry_delay_ms: int = 0
    alternative_route: Optional[str] = None


@dataclass
class DispatchConfig:
    """Configuration for strategy dispatch and re-dispatch."""
    # Timing
    max_execution_time_ms: int = 5000
    price_staleness_ms: int = 2000
    opportunity_ttl_ms: int = 10000

    # Re-dispatch policy
    max_retries: int = 3
    retry_delays_ms: list[int] = field(default_factory=lambda: [100, 500, 2000])
    enable_alternative_routes: bool = True
    enable_bridge_fallback: bool = True

    # Risk limits
    max_position_size: int = 10_000_000_000_000_000_000  # 10 ETH in wei
    max_daily_volume: int = 100_000_000_000_000_000_000  # 100 ETH in wei
    max_slippage_bps: int = 50  # 0.5%
    min_profit_bps: int = 10  # 0.1% minimum spread

    # Gas
    max_gas_price_gwei: int = 500
    gas_buffer_multiplier: float = 1.2

    # Circuit breaker
    circuit_breaker_threshold: int = 5  # Failures before opening
    circuit_breaker_timeout_ms: int = 30000  # 30s cooldown


@dataclass
class ChainState:
    """Per-chain state tracking."""
    chain_id: ChainId
    latest_block: int = 0
    latest_block_time_ns: int = 0
    gas_price: int = 0  # in wei
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_failure_ns: int = 0
    total_volume: int = 0
    total_profit: int = 0


@dataclass
class Position:
    """Current position in a token."""
    token: Token
    amount: int
    entry_price: int
    chain_id: ChainId
    opened_at_ns: int
    strategy_id: int = 0
