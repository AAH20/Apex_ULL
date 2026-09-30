"""
Arbitrage Engine
================

Main engine that orchestrates cross-chain arbitrage detection,
dispatch, and execution.

Pipeline:
    1. Price Feed → Opportunity Detector
    2. Detector → Risk Manager (pre-trade check)
    3. Risk Manager → Strategy Dispatcher
    4. Dispatcher → Cross Chain Router
    5. Router → Execution (simulated)
    6. Result → Risk Manager (post-trade update)
    7. Failed Result → Dispatcher (re-dispatch)

ULL Principles:
    - Single-threaded hot path (no locks needed)
    - Pre-allocated buffers
    - Cache-friendly data structures
    - Deterministic execution
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Callable
from collections import deque

from .models import (
    ChainId,
    Token,
    PriceUpdate,
    ArbitrageOpportunity,
    StrategyResult,
    DispatchConfig,
    OrderStatus,
    FailureReason,
    Position,
    ChainState,
)
from .detector import OpportunityDetector
from .dispatcher import StrategyDispatcher
from .risk import RiskManager
from .router import CrossChainRouter


class ArbitrageEngine:
    """
    Main cross-chain arbitrage engine.

    Orchestrates the full pipeline from price updates to
    strategy execution and re-dispatch.
    """

    def __init__(self, config: Optional[DispatchConfig] = None):
        self.config = config or DispatchConfig()

        # Core components
        self.detector = OpportunityDetector(self.config)
        self.dispatcher = StrategyDispatcher(self.config)
        self.risk_manager = RiskManager(self.config)
        self.router = CrossChainRouter()

        # Set up execution callback
        self.dispatcher.set_execution_callback(self._execute_strategy)

        # Price feed buffer (pre-allocated)
        self._price_buffer: deque = deque(maxlen=10000)

        # Chain states
        self._chain_states: Dict[int, ChainState] = {}

        # Running state
        self._is_running: bool = False
        self._main_loop_callback: Optional[Callable] = None

        # Stats
        self._start_time_ns: int = 0
        self._total_updates: int = 0
        self._total_opportunities: int = 0
        self._total_dispatched: int = 0
        self._total_executed: int = 0
        self._total_profit: int = 0

    def start(self) -> None:
        """Start the arbitrage engine."""
        self._is_running = True
        self._start_time_ns = time.perf_counter_ns()

    def stop(self) -> None:
        """Stop the arbitrage engine."""
        self._is_running = False

    def on_price_update(self, update: PriceUpdate) -> None:
        """
        Process a new price update.

        This is the main entry point for market data.
        """
        self._total_updates += 1
        self._price_buffer.append(update)
        self.detector.update_price(update)

    def run_cycle(self) -> List[StrategyResult]:
        """
        Run one cycle of the arbitrage pipeline.

        1. Scan for opportunities
        2. Risk check
        3. Dispatch
        4. Process queue
        5. Handle results

        Returns list of strategy results from this cycle.
        """
        results: List[StrategyResult] = []

        # Step 1: Scan for opportunities
        opportunities = self.detector.scan_opportunities()
        self._total_opportunities += len(opportunities)

        # Step 2 & 3: Risk check and dispatch
        for opp in opportunities:
            if self.risk_manager.check_opportunity(opp):
                if self.dispatcher.dispatch(opp):
                    self._total_dispatched += 1

        # Step 4: Process dispatch queue
        cycle_results = self.dispatcher.process_queue()
        results.extend(cycle_results)

        # Step 5: Update stats
        for result in cycle_results:
            if result.success:
                self._total_executed += 1
                self._total_profit += result.actual_profit

        return results

    def _execute_strategy(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Execute a single arbitrage strategy.

        In production, this would:
        1. Buy on source chain DEX
        2. Bridge tokens to destination chain
        3. Sell on destination chain DEX
        4. Bridge profits back

        For this implementation, we simulate execution.
        """
        # Find best route
        route = self.router.find_best_route(
            opportunity.buy_chain, opportunity.sell_chain
        )

        if route is None:
            opportunity.last_error = FailureReason.NETWORK_ERROR
            return False

        # Simulate execution with some randomness
        # In production, this would be actual blockchain interaction
        import random
        success = random.random() < 0.7  # 70% success rate

        if success:
            opportunity.status = OrderStatus.COMPLETED
            self.risk_manager.on_strategy_result(
                opportunity, True, opportunity.estimated_profit
            )
            self.router.report_route_result(
                route.route_id, True, route.estimated_time_ms, route.estimated_fee
            )
        else:
            # Determine failure reason
            failure_roll = random.random()
            if failure_roll < 0.3:
                opportunity.last_error = FailureReason.PRICE_MOVED
            elif failure_roll < 0.5:
                opportunity.last_error = FailureReason.INSUFFICIENT_LIQUIDITY
            elif failure_roll < 0.7:
                opportunity.last_error = FailureReason.GAS_TOO_HIGH
            elif failure_roll < 0.85:
                opportunity.last_error = FailureReason.SLIPPAGE_EXCEEDED
            else:
                opportunity.last_error = FailureReason.BRIDGE_TIMEOUT

            self.risk_manager.on_strategy_result(opportunity, False)
            self.router.report_route_result(
                route.route_id, False, route.estimated_time_ms, route.estimated_fee
            )

        return success

    def get_stats(self) -> Dict[str, int]:
        """Get engine statistics."""
        elapsed_ns = time.perf_counter_ns() - self._start_time_ns
        elapsed_s = elapsed_ns / 1_000_000_000

        return {
            "running": int(self._is_running),
            "elapsed_seconds": int(elapsed_s),
            "total_updates": self._total_updates,
            "total_opportunities": self._total_opportunities,
            "total_dispatched": self._total_dispatched,
            "total_executed": self._total_executed,
            "total_profit": self._total_profit,
            "detector": self.detector.get_stats(),
            "dispatcher": self.dispatcher.get_stats(),
            "risk": self.risk_manager.get_stats(),
        }

    def get_chain_state(self, chain_id: ChainId) -> ChainState:
        """Get the current state of a chain."""
        if int(chain_id) not in self._chain_states:
            self._chain_states[int(chain_id)] = ChainState(chain_id=chain_id)
        return self._chain_states[int(chain_id)]
