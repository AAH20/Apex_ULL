"""
Cross-Chain Router
==================

Routes orders across chains via bridges and DEXs.

Supports multiple bridge protocols and DEX aggregators:
    - Bridges: Arbitrum Bridge, Optimism Bridge, Hop Protocol, Celer cBridge, Stargate
    - DEXs: Uniswap V2/V3, SushiSwap, PancakeSwap, QuickSwap, TraderJoe

Routing Strategy:
    1. Direct bridge if available and cheap
    2. DEX on source chain → Bridge → DEX on destination chain
    3. Multi-hop via intermediate chain if cheaper

ULL Optimizations:
    - Pre-computed route cache
    - Lock-free route selection
    - Minimal allocations on hot path
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .models import ChainId, Token, ArbitrageOpportunity


@dataclass
class Route:
    """A cross-chain route."""
    route_id: str
    source_chain: ChainId
    dest_chain: ChainId
    bridge: str
    source_dex: str
    dest_dex: str
    estimated_time_ms: int
    estimated_fee: int
    is_active: bool = True


@dataclass
class RouteMetrics:
    """Metrics for route quality."""
    success_rate: float
    avg_time_ms: int
    avg_fee: int
    last_used_ns: int


class CrossChainRouter:
    """
    Routes cross-chain transactions through optimal paths.

    Maintains a cache of known routes and their performance metrics,
    selecting the best route for each opportunity.
    """

    def __init__(self):
        # Route cache: (source_chain, dest_chain) -> list of Route
        self._routes: Dict[Tuple[int, int], List[Route]] = {}

        # Route metrics: route_id -> RouteMetrics
        self._metrics: Dict[str, RouteMetrics] = {}

        # DEX registry: chain_id -> list of DEX IDs
        self._dex_registry: Dict[int, List[str]] = {
            int(ChainId.ETHEREUM): ["uniswap_v3", "uniswap_v2", "sushiswap", "curve"],
            int(ChainId.BSC): ["pancakeswap", "biswap", "sushiswap"],
            int(ChainId.POLYGON): ["quickswap", "sushiswap", "uniswap_v3"],
            int(ChainId.ARBITRUM): ["uniswap_v3", "sushiswap", "gmx"],
            int(ChainId.OPTIMISM): ["uniswap_v3", "sushiswap", "velodrome"],
            int(ChainId.AVALANCHE): ["traderjoe", "pangolin", "sushiswap"],
            int(ChainId.BASE): ["uniswap_v3", "sushiswap", "aerodrome"],
        }

        # Bridge registry: (source, dest) -> bridge name
        self._bridges: Dict[Tuple[int, int], str] = {
            (int(ChainId.ETHEREUM), int(ChainId.ARBITRUM)): "arbitrum_bridge",
            (int(ChainId.ARBITRUM), int(ChainId.ETHEREUM)): "arbitrum_bridge",
            (int(ChainId.ETHEREUM), int(ChainId.OPTIMISM)): "optimism_bridge",
            (int(ChainId.OPTIMISM), int(ChainId.ETHEREUM)): "optimism_bridge",
            (int(ChainId.ETHEREUM), int(ChainId.BSC)): "bsc_bridge",
            (int(ChainId.BSC), int(ChainId.ETHEREUM)): "bsc_bridge",
            (int(ChainId.ETHEREUM), int(ChainId.POLYGON)): "polygon_bridge",
            (int(ChainId.POLYGON), int(ChainId.ETHEREUM)): "polygon_bridge",
            (int(ChainId.ETHEREUM), int(ChainId.AVALANCHE)): "cbridge",
            (int(ChainId.AVALANCHE), int(ChainId.ETHEREUM)): "cbridge",
            (int(ChainId.ETHEREUM), int(ChainId.BASE)): "base_bridge",
            (int(ChainId.BASE), int(ChainId.ETHEREUM)): "base_bridge",
            (int(ChainId.ARBITRUM), int(ChainId.OPTIMISM)): "hop_protocol",
            (int(ChainId.OPTIMISM), int(ChainId.ARBITRUM)): "hop_protocol",
            (int(ChainId.BSC), int(ChainId.POLYGON)): "cbridge",
            (int(ChainId.POLYGON), int(ChainId.BSC)): "cbridge",
        }

        # Initialize default routes
        self._init_default_routes()

    def find_best_route(
        self, source_chain: ChainId, dest_chain: ChainId
    ) -> Optional[Route]:
        """
        Find the best route between two chains.

        Considers: fee, time, success rate.
        """
        key = (int(source_chain), int(dest_chain))
        routes = self._routes.get(key, [])

        if not routes:
            return None

        # Filter active routes
        active_routes = [r for r in routes if r.is_active]
        if not active_routes:
            return None

        # Score routes: lower is better
        best_route = None
        best_score = float("inf")

        for route in active_routes:
            metrics = self._metrics.get(route.route_id)
            if metrics is None:
                score = route.estimated_fee + route.estimated_time_ms * 1_000_000
            else:
                # Weighted score
                fee_score = route.estimated_fee
                time_score = route.estimated_time_ms * 1_000_000
                success_score = (1.0 - metrics.success_rate) * 1_000_000_000_000
                score = fee_score + time_score + success_score

            if score < best_score:
                best_score = score
                best_route = route

        return best_route

    def find_alternative_route(
        self, source_chain: ChainId, dest_chain: ChainId, exclude_route_id: str
    ) -> Optional[Route]:
        """Find an alternative route excluding the given one."""
        key = (int(source_chain), int(dest_chain))
        routes = self._routes.get(key, [])

        for route in routes:
            if route.route_id != exclude_route_id and route.is_active:
                return route

        return None

    def get_dexes_for_chain(self, chain_id: ChainId) -> List[str]:
        """Get available DEXs for a chain."""
        return self._dex_registry.get(int(chain_id), [])

    def get_bridge_for_pair(
        self, source_chain: ChainId, dest_chain: ChainId
    ) -> Optional[str]:
        """Get the bridge for a chain pair."""
        return self._bridges.get((int(source_chain), int(dest_chain)))

    def report_route_result(
        self, route_id: str, success: bool, time_ms: int, fee: int
    ) -> None:
        """Report the result of using a route for learning."""
        metrics = self._metrics.get(route_id)
        if metrics is None:
            self._metrics[route_id] = RouteMetrics(
                success_rate=1.0 if success else 0.0,
                avg_time_ms=time_ms,
                avg_fee=fee,
                last_used_ns=time.perf_counter_ns(),
            )
        else:
            # Exponential moving average
            alpha = 0.3
            metrics.success_rate = (
                alpha * (1.0 if success else 0.0) + (1 - alpha) * metrics.success_rate
            )
            metrics.avg_time_ms = int(alpha * time_ms + (1 - alpha) * metrics.avg_time_ms)
            metrics.avg_fee = int(alpha * fee + (1 - alpha) * metrics.avg_fee)
            metrics.last_used_ns = time.perf_counter_ns()

    def _init_default_routes(self) -> None:
        """Initialize default routes for known chain pairs."""
        for (src, dst), bridge in self._bridges.items():
            route_id = f"{bridge}_{src}_{dst}"
            route = Route(
                route_id=route_id,
                source_chain=ChainId(src),
                dest_chain=ChainId(dst),
                bridge=bridge,
                source_dex=self._dex_registry.get(src, ["uniswap_v3"])[0],
                dest_dex=self._dex_registry.get(dst, ["uniswap_v3"])[0],
                estimated_time_ms=15000,  # 15 seconds default
                estimated_fee=5_000_000_000_000_000,  # 0.005 ETH default
            )
            key = (src, dst)
            if key not in self._routes:
                self._routes[key] = []
            self._routes[key].append(route)
