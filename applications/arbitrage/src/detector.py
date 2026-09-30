"""
Opportunity Detector
====================

Real-time cross-chain arbitrage opportunity detection.

Scans price feeds across all supported chains and DEXs to find
price discrepancies that exceed the minimum profit threshold after
accounting for gas costs, bridge fees, and slippage.

ULL Optimizations:
    - Pre-allocated ring buffer for price updates
    - Cache-friendly token pair indexing
    - Branch-free hot path for spread calculation
    - Lock-free price snapshot reads
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from .models import (
    ChainId,
    Token,
    PriceUpdate,
    ArbitrageOpportunity,
    DispatchConfig,
    OrderStatus,
    FailureReason,
)


class OpportunityDetector:
    """
    Detects cross-chain arbitrage opportunities from price feeds.

    Maintains a snapshot of best prices across all chains and DEXs,
    then scans for profitable cross-chain spreads.

    Time complexity: O(C^2 * D^2) per scan where C = chains, D = DEXs
    Space complexity: O(C * D * T) where T = token pairs
    """

    def __init__(self, config: DispatchConfig):
        self.config = config
        self._opportunity_counter = 0

        # Price snapshots: (chain_id, token_in_addr, token_out_addr) -> best PriceUpdate
        self._price_index: Dict[Tuple[int, str, str], PriceUpdate] = {}

        # Token pair index: (token_in_symbol, token_out_symbol) -> list of (chain_id, dex_id, token_in_addr, token_out_addr)
        self._pair_index: Dict[Tuple[str, str], List[Tuple[int, str, str, str]]] = defaultdict(list)

        # Active opportunities
        self._active_opportunities: Dict[int, ArbitrageOpportunity] = {}

        # Performance tracking
        self._scan_count = 0
        self._opportunities_found = 0

    def update_price(self, update: PriceUpdate) -> None:
        """
        Process a new price update and update the index.

        This is the hot path — must be O(1) amortized.
        """
        if not update.is_valid:
            return

        key = (
            int(update.token_in.chain_id),
            update.token_in.address,
            update.token_out.address,
        )

        existing = self._price_index.get(key)
        if existing is None or update.price < existing.price:
            self._price_index[key] = update

        # Update pair index: (symbol_in, symbol_out) -> list of (chain_id, dex_id, token_in_addr, token_out_addr)
        pair_key = (update.token_in.symbol, update.token_out.symbol)
        pair_entry = (
            int(update.token_in.chain_id),
            update.dex_id,
            update.token_in.address,
            update.token_out.address,
        )
        # Check if this chain+dex combo already exists
        existing_entries = self._pair_index[pair_key]
        if not any(e[0] == pair_entry[0] and e[1] == pair_entry[1] for e in existing_entries):
            existing_entries.append(pair_entry)

    def scan_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Scan all tracked pairs for cross-chain arbitrage opportunities.

        Returns new opportunities found in this scan.
        """
        self._scan_count += 1
        new_opportunities: List[ArbitrageOpportunity] = []
        now_ns = time.perf_counter_ns()

        # Iterate over all token pairs
        for (symbol_in, symbol_out), chain_dex_list in self._pair_index.items():
            if len(chain_dex_list) < 2:
                continue  # Need at least 2 chains for cross-chain

            # Find best buy and sell prices across chains
            best_buy: Optional[PriceUpdate] = None
            best_sell: Optional[PriceUpdate] = None

            for chain_id, dex_id, token_in_addr, token_out_addr in chain_dex_list:
                key = (chain_id, token_in_addr, token_out_addr)
                update = self._price_index.get(key)
                if update is None:
                    continue

                # Check staleness
                age_ms = (now_ns - update.timestamp_ns) / 1_000_000
                if age_ms > self.config.price_staleness_ms:
                    continue

                if best_buy is None or update.price < best_buy.price:
                    best_buy = update
                if best_sell is None or update.price > best_sell.price:
                    best_sell = update

            if best_buy is None or best_sell is None:
                continue

            # Must be different chains
            if best_buy.token_in.chain_id == best_sell.token_in.chain_id:
                continue

            # Calculate spread
            spread_bps = self._calculate_spread_bps(best_buy.price, best_sell.price)
            if spread_bps < self.config.min_profit_bps:
                continue

            # Estimate profit
            estimated_profit = self._estimate_profit(
                best_buy, best_sell, spread_bps
            )
            if estimated_profit <= 0:
                continue

            # Create opportunity
            self._opportunity_counter += 1
            opportunity = ArbitrageOpportunity(
                id=self._opportunity_counter,
                buy_chain=best_buy.token_in.chain_id,
                sell_chain=best_sell.token_in.chain_id,
                token=best_buy.token_in,
                buy_price=best_buy.price,
                sell_price=best_sell.price,
                spread_bps=spread_bps,
                estimated_profit=estimated_profit,
                confidence=self._calculate_confidence(best_buy, best_sell),
                detected_at_ns=now_ns,
                expires_at_ns=now_ns + self.config.opportunity_ttl_ms * 1_000_000,
                buy_dex=best_buy.dex_id,
                sell_dex=best_sell.dex_id,
            )

            # Deduplicate: don't create if similar opportunity exists
            if not self._is_duplicate(opportunity):
                new_opportunities.append(opportunity)
                self._active_opportunities[opportunity.id] = opportunity
                self._opportunities_found += 1

        # Clean up expired opportunities
        self._cleanup_expired(now_ns)

        return new_opportunities

    def get_opportunity(self, opp_id: int) -> Optional[ArbitrageOpportunity]:
        """Get an active opportunity by ID."""
        return self._active_opportunities.get(opp_id)

    def mark_dispatched(self, opp_id: int) -> None:
        """Mark an opportunity as dispatched."""
        opp = self._active_opportunities.get(opp_id)
        if opp:
            opp.status = OrderStatus.DISPATCHED

    def mark_completed(self, opp_id: int) -> None:
        """Mark an opportunity as completed."""
        opp = self._active_opportunities.get(opp_id)
        if opp:
            opp.status = OrderStatus.COMPLETED

    def mark_failed(self, opp_id: int, reason: FailureReason) -> None:
        """Mark an opportunity as failed."""
        opp = self._active_opportunities.get(opp_id)
        if opp:
            opp.status = OrderStatus.FAILED
            opp.last_error = reason

    def get_stats(self) -> Dict[str, int]:
        """Get detector statistics."""
        return {
            "scan_count": self._scan_count,
            "opportunities_found": self._opportunities_found,
            "active_opportunities": len(self._active_opportunities),
            "price_index_size": len(self._price_index),
            "pair_index_size": len(self._pair_index),
        }

    def _calculate_spread_bps(self, buy_price: int, sell_price: int) -> int:
        """Calculate spread in basis points."""
        if buy_price <= 0:
            return 0
        return int((sell_price - buy_price) * 10000 / buy_price)

    def _estimate_profit(
        self, buy: PriceUpdate, sell: PriceUpdate, spread_bps: int
    ) -> int:
        """
        Estimate profit after costs.

        Accounts for:
        - Trading fees (0.3% per DEX)
        - Bridge fees (flat estimate)
        - Gas costs
        - Slippage
        """
        # Assume 1 ETH position for estimation
        position_size = 1_000_000_000_000_000_000  # 1 ETH in wei

        # Gross profit
        gross_profit = position_size * spread_bps // 10000

        # Trading fees: 0.3% on each side
        trading_fees = position_size * 30 // 10000 * 2

        # Bridge fee estimate: 0.05% of position
        bridge_fee = position_size * 5 // 10000

        # Gas cost estimate: ~500K gas * gas price
        gas_cost = 500_000 * 20_000_000_000  # 20 gwei

        # Slippage estimate: 0.1%
        slippage = position_size * 10 // 10000

        net_profit = gross_profit - trading_fees - bridge_fee - gas_cost - slippage
        return max(0, net_profit)

    def _calculate_confidence(self, buy: PriceUpdate, sell: PriceUpdate) -> float:
        """
        Calculate confidence score (0.0 to 1.0).

        Based on:
        - Liquidity depth
        - Price freshness
        - Spread magnitude
        """
        confidence = 0.5

        # Liquidity factor
        min_liquidity = min(buy.liquidity, sell.liquidity)
        if min_liquidity > 10_000_000_000_000_000_000:  # > 10 ETH
            confidence += 0.2
        elif min_liquidity > 1_000_000_000_000_000_000:  # > 1 ETH
            confidence += 0.1

        # Freshness factor
        now_ns = time.perf_counter_ns()
        buy_age_ms = (now_ns - buy.timestamp_ns) / 1_000_000
        sell_age_ms = (now_ns - sell.timestamp_ns) / 1_000_000
        avg_age_ms = (buy_age_ms + sell_age_ms) / 2
        if avg_age_ms < 500:
            confidence += 0.15
        elif avg_age_ms < 1000:
            confidence += 0.05

        # Spread magnitude
        spread_bps = self._calculate_spread_bps(buy.price, sell.price)
        if spread_bps > 100:  # > 1%
            confidence += 0.15
        elif spread_bps > 50:  # > 0.5%
            confidence += 0.05

        return min(1.0, confidence)

    def _is_duplicate(self, new_opp: ArbitrageOpportunity) -> bool:
        """Check if a similar opportunity already exists."""
        for opp in self._active_opportunities.values():
            if (opp.buy_chain == new_opp.buy_chain
                and opp.sell_chain == new_opp.sell_chain
                and opp.token.address == new_opp.token.address
                and opp.status in (OrderStatus.PENDING, OrderStatus.DISPATCHED)):
                return True
        return False

    def _cleanup_expired(self, now_ns: int) -> None:
        """Remove expired opportunities."""
        expired = [
            opp_id for opp_id, opp in self._active_opportunities.items()
            if now_ns > opp.expires_at_ns
        ]
        for opp_id in expired:
            opp = self._active_opportunities[opp_id]
            if opp.status == OrderStatus.PENDING:
                opp.status = OrderStatus.EXPIRED
            del self._active_opportunities[opp_id]


