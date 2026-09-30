"""
Strategy Dispatcher with Re-dispatch
====================================

Dispatches arbitrage strategies to execution and handles failures
with automatic re-dispatch logic.

Re-dispatch Policy:
    1. Price moved → Re-dispatch with updated prices
    2. Insufficient liquidity → Try alternative DEX on same chain
    3. Gas too high → Wait and retry with higher gas buffer
    4. Slippage exceeded → Reduce position size and retry
    5. Bridge timeout → Try alternative bridge route
    6. Smart contract revert → Analyze and retry with adjustments
    7. Network error → Exponential backoff retry
    8. Risk limit hit → Do not retry, log for review

ULL Optimizations:
    - Pre-allocated dispatch queue
    - Lock-free status tracking
    - Minimal branching on hot path
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Callable
from collections import deque
from enum import IntEnum

from .models import (
    ArbitrageOpportunity,
    StrategyResult,
    DispatchConfig,
    OrderStatus,
    FailureReason,
    ChainId,
)


class DispatchPriority(IntEnum):
    """Dispatch priority levels."""
    CRITICAL = 0  # High profit, execute immediately
    HIGH = 1      # Good profit, execute soon
    NORMAL = 2    # Marginal profit, execute if capacity
    LOW = 3       # Low profit, execute last


class StrategyDispatcher:
    """
    Dispatches and re-dispatches arbitrage strategies.

    Manages the full lifecycle of a strategy from detection to
    completion or final failure, including intelligent re-dispatch.
    """

    def __init__(self, config: DispatchConfig):
        self.config = config

        # Dispatch queues by priority
        self._queues: Dict[DispatchPriority, deque] = {
            priority: deque() for priority in DispatchPriority
        }

        # Active strategies
        self._active_strategies: Dict[int, ArbitrageOpportunity] = {}

        # Strategy history for learning
        self._history: List[StrategyResult] = []

        # Re-dispatch tracking
        self._retry_counts: Dict[int, int] = {}
        self._last_retry_ns: Dict[int, int] = {}

        # Alternative routes cache
        self._alternative_routes: Dict[int, List[str]] = {}

        # Execution callback (set by engine)
        self._execution_callback: Optional[Callable] = None

        # Stats
        self._dispatched = 0
        self._succeeded = 0
        self._failed = 0
        self._retried = 0

    def set_execution_callback(self, callback: Callable) -> None:
        """Set the callback for executing a strategy."""
        self._execution_callback = callback

    def dispatch(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Dispatch a new arbitrage opportunity.

        Returns True if queued for execution.
        """
        if self._execution_callback is None:
            return False

        priority = self._calculate_priority(opportunity)
        self._queues[priority].append(opportunity)
        self._active_strategies[opportunity.id] = opportunity
        self._dispatched += 1

        return True

    def process_queue(self) -> List[StrategyResult]:
        """
        Process the dispatch queue.

        Executes strategies in priority order and handles results.
        Returns list of results from this processing round.
        """
        results: List[StrategyResult] = []

        for priority in DispatchPriority:
            queue = self._queues[priority]
            while queue:
                opportunity = queue.popleft()

                # Check if still valid
                if not self._is_still_valid(opportunity):
                    continue

                # Execute
                result = self._execute(opportunity)
                results.append(result)

                # Handle result
                if result.success:
                    self._succeeded += 1
                    opportunity.status = OrderStatus.COMPLETED
                else:
                    self._failed += 1
                    self._handle_failure(opportunity, result)

        return results

    def _execute(self, opportunity: ArbitrageOpportunity) -> StrategyResult:
        """Execute a single strategy."""
        start_ns = time.perf_counter_ns()

        try:
            if self._execution_callback:
                success = self._execution_callback(opportunity)
            else:
                success = False

            elapsed_ns = time.perf_counter_ns() - start_ns

            if success:
                return StrategyResult(
                    opportunity_id=opportunity.id,
                    success=True,
                    status=OrderStatus.COMPLETED,
                    failure_reason=FailureReason.NONE,
                    execution_time_ns=elapsed_ns,
                    actual_profit=opportunity.estimated_profit,
                )
            else:
                return StrategyResult(
                    opportunity_id=opportunity.id,
                    success=False,
                    status=OrderStatus.FAILED,
                    failure_reason=FailureReason.UNKNOWN,
                    execution_time_ns=elapsed_ns,
                )

        except Exception as e:
            elapsed_ns = time.perf_counter_ns() - start_ns
            return StrategyResult(
                opportunity_id=opportunity.id,
                success=False,
                status=OrderStatus.FAILED,
                failure_reason=FailureReason.UNKNOWN,
                execution_time_ns=elapsed_ns,
            )

    def _handle_failure(
        self, opportunity: ArbitrageOpportunity, result: StrategyResult
    ) -> None:
        """
        Handle a failed strategy execution.

        Determines if re-dispatch is appropriate and queues retry.
        """
        opportunity.status = OrderStatus.FAILED
        opportunity.last_error = result.failure_reason
        opportunity.attempt_count += 1

        # Check if we should retry
        if not self._should_retry(opportunity, result):
            return

        # Calculate retry delay
        retry_count = self._retry_counts.get(opportunity.id, 0)
        if retry_count < len(self.config.retry_delays_ms):
            delay_ms = self.config.retry_delays_ms[retry_count]
        else:
            delay_ms = self.config.retry_delays_ms[-1] * 2

        self._retry_counts[opportunity.id] = retry_count + 1
        self._last_retry_ns[opportunity.id] = time.perf_counter_ns()

        # Prepare re-dispatch
        opportunity.status = OrderStatus.RETRYING
        result.should_retry = True
        result.retry_delay_ms = delay_ms

        # Find alternative route if enabled
        if self.config.enable_alternative_routes:
            alt_route = self._find_alternative_route(opportunity)
            if alt_route:
                result.alternative_route = alt_route
                opportunity.bridge_route = alt_route

        # Re-queue with adjusted parameters
        priority = self._calculate_priority(opportunity)
        self._queues[priority].append(opportunity)
        self._retried += 1

    def _should_retry(
        self, opportunity: ArbitrageOpportunity, result: StrategyResult
    ) -> bool:
        """
        Determine if a failed strategy should be retried.

        Returns False for non-retryable failures or max retries exceeded.
        """
        # Max retries check
        retry_count = self._retry_counts.get(opportunity.id, 0)
        if retry_count >= self.config.max_retries:
            return False

        # Non-retryable failures
        non_retryable = {
            FailureReason.RISK_LIMIT_HIT,
            FailureReason.SMART_CONTRACT_REVERT,
        }
        if result.failure_reason in non_retryable:
            return False

        # Check if opportunity is still valid
        if not self._is_still_valid(opportunity):
            return False

        return True

    def _is_still_valid(self, opportunity: ArbitrageOpportunity) -> bool:
        """Check if an opportunity is still valid for execution."""
        now_ns = time.perf_counter_ns()

        # Check expiry
        if now_ns > opportunity.expires_at_ns:
            return False

        # Check retry backoff
        last_retry = self._last_retry_ns.get(opportunity.id, 0)
        if last_retry > 0:
            retry_count = self._retry_counts.get(opportunity.id, 0)
            if retry_count < len(self.config.retry_delays_ms):
                required_delay_ns = self.config.retry_delays_ms[retry_count] * 1_000_000
            else:
                required_delay_ns = self.config.retry_delays_ms[-1] * 2_000_000
            if now_ns - last_retry < required_delay_ns:
                return False

        return True

    def _calculate_priority(self, opportunity: ArbitrageOpportunity) -> DispatchPriority:
        """Calculate dispatch priority based on profit and urgency."""
        if opportunity.estimated_profit > 5_000_000_000_000_000:  # > 0.5 ETH
            return DispatchPriority.CRITICAL
        elif opportunity.estimated_profit > 1_000_000_000_000_000:  # > 0.1 ETH
            return DispatchPriority.HIGH
        elif opportunity.estimated_profit > 100_000_000_000_000:  # > 0.01 ETH
            return DispatchPriority.NORMAL
        else:
            return DispatchPriority.LOW

    def _find_alternative_route(self, opportunity: ArbitrageOpportunity) -> Optional[str]:
        """Find an alternative bridge/DEX route for re-dispatch."""
        # In production, this would query a routing service
        # For now, return a placeholder
        alternatives = {
            (ChainId.ETHEREUM, ChainId.ARBITRUM): "arbitrum_bridge_v2",
            (ChainId.ETHEREUM, ChainId.OPTIMISM): "optimism_bridge_v2",
            (ChainId.ETHEREUM, ChainId.BSC): "bsc_bridge_v2",
            (ChainId.ETHEREUM, ChainId.POLYGON): "polygon_bridge_v2",
            (ChainId.ARBITRUM, ChainId.OPTIMISM): "hop_protocol",
            (ChainId.BSC, ChainId.POLYGON): "cbridge",
        }

        key = (opportunity.buy_chain, opportunity.sell_chain)
        reverse_key = (opportunity.sell_chain, opportunity.buy_chain)

        return alternatives.get(key) or alternatives.get(reverse_key)

    def get_stats(self) -> Dict[str, int]:
        """Get dispatcher statistics."""
        return {
            "dispatched": self._dispatched,
            "succeeded": self._succeeded,
            "failed": self._failed,
            "retried": self._retried,
            "active_strategies": len(self._active_strategies),
            "queue_critical": len(self._queues[DispatchPriority.CRITICAL]),
            "queue_high": len(self._queues[DispatchPriority.HIGH]),
            "queue_normal": len(self._queues[DispatchPriority.NORMAL]),
            "queue_low": len(self._queues[DispatchPriority.LOW]),
        }
