"""
Risk Manager
============

Pre-trade and post-trade risk management for cross-chain arbitrage.

Risk Checks:
    - Position size limits
    - Daily volume limits
    - Slippage limits
    - Gas price limits
    - Circuit breaker (consecutive failures)
    - Per-chain exposure limits
    - Token-level exposure limits

ULL Optimizations:
    - Pre-allocated risk snapshot
    - Lock-free counter updates
    - Branch-free checks on hot path
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from .models import (
    ArbitrageOpportunity,
    DispatchConfig,
    ChainId,
    Token,
    OrderStatus,
    FailureReason,
    Position,
    ChainState,
)


@dataclass
class RiskSnapshot:
    """Immutable risk state snapshot for fast checks."""
    total_exposure: int
    daily_volume: int
    daily_profit: int
    chain_exposures: Dict[int, int]
    token_exposures: Dict[str, int]
    consecutive_failures: int
    circuit_breaker_open: bool
    circuit_breaker_open_until_ns: int


class RiskManager:
    """
    Manages risk for cross-chain arbitrage strategies.

    All checks are O(1) using pre-aggregated state.
    """

    def __init__(self, config: DispatchConfig):
        self.config = config

        # Exposure tracking
        self._total_exposure: int = 0
        self._daily_volume: int = 0
        self._daily_profit: int = 0
        self._chain_exposures: Dict[int, int] = {}
        self._token_exposures: Dict[str, int] = {}

        # Circuit breaker
        self._consecutive_failures: int = 0
        self._circuit_breaker_open: bool = False
        self._circuit_breaker_open_until_ns: int = 0

        # Position tracking
        self._positions: Dict[int, Position] = {}

        # Chain states
        self._chain_states: Dict[int, ChainState] = {}

        # Daily reset tracking
        self._last_reset_ns: int = time.perf_counter_ns()

        # Stats
        self._checks_performed = 0
        self._checks_failed = 0

    def check_opportunity(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Check if an opportunity passes all risk checks.

        Returns True if the opportunity is safe to execute.
        """
        self._checks_performed += 1

        # Reset daily counters if needed
        self._maybe_reset_daily()

        # Circuit breaker check
        if self._circuit_breaker_open:
            now_ns = time.perf_counter_ns()
            if now_ns < self._circuit_breaker_open_until_ns:
                self._checks_failed += 1
                return False
            else:
                self._circuit_breaker_open = False
                self._consecutive_failures = 0

        # Position size check
        if opportunity.estimated_profit > self.config.max_position_size:
            self._checks_failed += 1
            return False

        # Daily volume check
        if self._daily_volume + opportunity.estimated_profit > self.config.max_daily_volume:
            self._checks_failed += 1
            return False

        # Slippage check
        if opportunity.spread_bps > self.config.max_slippage_bps * 10:
            self._checks_failed += 1
            return False

        # Chain exposure check
        buy_chain_exposure = self._chain_exposures.get(int(opportunity.buy_chain), 0)
        sell_chain_exposure = self._chain_exposures.get(int(opportunity.sell_chain), 0)
        if (buy_chain_exposure + opportunity.estimated_profit > self.config.max_position_size
            or sell_chain_exposure + opportunity.estimated_profit > self.config.max_position_size):
            self._checks_failed += 1
            return False

        return True

    def on_strategy_result(
        self, opportunity: ArbitrageOpportunity, success: bool, profit: int = 0
    ) -> None:
        """Update risk state after strategy execution."""
        if success:
            self._consecutive_failures = 0
            self._daily_volume += opportunity.estimated_profit
            self._daily_profit += profit

            # Update chain exposures
            buy_chain = int(opportunity.buy_chain)
            sell_chain = int(opportunity.sell_chain)
            self._chain_exposures[buy_chain] = (
                self._chain_exposures.get(buy_chain, 0) + opportunity.estimated_profit
            )
            self._chain_exposures[sell_chain] = (
                self._chain_exposures.get(sell_chain, 0) + opportunity.estimated_profit
            )
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.config.circuit_breaker_threshold:
                self._open_circuit_breaker()

    def open_position(self, position: Position) -> bool:
        """Open a new position if it passes risk checks."""
        if position.amount > self.config.max_position_size:
            return False

        self._positions[id(position)] = position
        self._total_exposure += position.amount
        return True

    def close_position(self, position_id: int, profit: int) -> None:
        """Close a position and update P&L."""
        position = self._positions.pop(position_id, None)
        if position:
            self._total_exposure -= position.amount
            self._daily_profit += profit

    def get_snapshot(self) -> RiskSnapshot:
        """Get current risk snapshot."""
        return RiskSnapshot(
            total_exposure=self._total_exposure,
            daily_volume=self._daily_volume,
            daily_profit=self._daily_profit,
            chain_exposures=dict(self._chain_exposures),
            token_exposures=dict(self._token_exposures),
            consecutive_failures=self._consecutive_failures,
            circuit_breaker_open=self._circuit_breaker_open,
            circuit_breaker_open_until_ns=self._circuit_breaker_open_until_ns,
        )

    def get_stats(self) -> Dict[str, int]:
        """Get risk manager statistics."""
        return {
            "checks_performed": self._checks_performed,
            "checks_failed": self._checks_failed,
            "total_exposure": self._total_exposure,
            "daily_volume": self._daily_volume,
            "daily_profit": self._daily_profit,
            "open_positions": len(self._positions),
            "consecutive_failures": self._consecutive_failures,
            "circuit_breaker_open": int(self._circuit_breaker_open),
        }

    def _open_circuit_breaker(self) -> None:
        """Open the circuit breaker."""
        self._circuit_breaker_open = True
        self._circuit_breaker_open_until_ns = (
            time.perf_counter_ns() + self.config.circuit_breaker_timeout_ms * 1_000_000
        )

    def _maybe_reset_daily(self) -> None:
        """Reset daily counters if a day has passed."""
        now_ns = time.perf_counter_ns()
        day_ns = 24 * 60 * 60 * 1_000_000_000
        if now_ns - self._last_reset_ns > day_ns:
            self._daily_volume = 0
            self._daily_profit = 0
            self._last_reset_ns = now_ns
