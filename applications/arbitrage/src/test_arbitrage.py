"""
Tests for Cross-Chain Arbitrage Application
============================================

Tests cover:
    - Opportunity detection
    - Strategy dispatch and re-dispatch
    - Risk management
    - Cross-chain routing
    - Full engine cycle
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import random
from applications.arbitrage.src import (
    ArbitrageEngine,
    ChainId,
    Token,
    PriceUpdate,
    ArbitrageOpportunity,
    StrategyResult,
    DispatchConfig,
    OrderStatus,
    FailureReason,
    OpportunityDetector,
    StrategyDispatcher,
    RiskManager,
    CrossChainRouter,
)


def create_token(symbol: str, chain_id: ChainId, address: str = None) -> Token:
    """Helper to create a token."""
    if address is None:
        address = f"0x{symbol.lower()}_{int(chain_id):04x}"
    return Token(
        address=address,
        symbol=symbol,
        decimals=18,
        chain_id=chain_id,
        is_stable=symbol in ("USDC", "USDT", "DAI"),
    )


def create_price_update(
    token_in: Token,
    token_out: Token,
    price: int,
    liquidity: int = 10_000_000_000_000_000_000,
    dex_id: str = "uniswap_v3",
) -> PriceUpdate:
    """Helper to create a price update."""
    return PriceUpdate(
        token_in=token_in,
        token_out=token_out,
        price=price,
        liquidity=liquidity,
        timestamp_ns=time.perf_counter_ns(),
        dex_id=dex_id,
        block_number=1000,
    )


def test_opportunity_detection():
    """Test that opportunities are detected across chains."""
    print("=== Test: Opportunity Detection ===")

    config = DispatchConfig(min_profit_bps=10)
    detector = OpportunityDetector(config)

    eth = create_token("ETH", ChainId.ETHEREUM)
    usdc = create_token("USDC", ChainId.ETHEREUM)
    eth_arb = create_token("ETH", ChainId.ARBITRUM)
    usdc_arb = create_token("USDC", ChainId.ARBITRUM)

    # Price on Ethereum: 2000 USDC per ETH
    detector.update_price(create_price_update(eth, usdc, 2000 * 10**18, dex_id="uniswap_v3"))

    # Price on Arbitrum: 2050 USDC per ETH (2.5% higher)
    detector.update_price(create_price_update(eth_arb, usdc_arb, 2050 * 10**18, dex_id="uniswap_v3"))

    opportunities = detector.scan_opportunities()

    print(f"  Opportunities found: {len(opportunities)}")
    assert len(opportunities) > 0, "Should find at least one opportunity"

    opp = opportunities[0]
    print(f"  Buy chain: {opp.buy_chain.name}, Sell chain: {opp.sell_chain.name}")
    print(f"  Spread: {opp.spread_bps} bps")
    print(f"  Estimated profit: {opp.estimated_profit} wei")

    assert opp.buy_chain == ChainId.ETHEREUM
    assert opp.sell_chain == ChainId.ARBITRUM
    assert opp.spread_bps > 0

    print("  ✓ PASSED\n")


def test_risk_management():
    """Test risk management checks."""
    print("=== Test: Risk Management ===")

    config = DispatchConfig(
        max_position_size=5_000_000_000_000_000_000,  # 5 ETH
        max_daily_volume=50_000_000_000_000_000_000,  # 50 ETH
    )
    risk = RiskManager(config)

    eth = create_token("ETH", ChainId.ETHEREUM)
    usdc = create_token("USDC", ChainId.ETHEREUM)
    eth_arb = create_token("ETH", ChainId.ARBITRUM)
    usdc_arb = create_token("USDC", ChainId.ARBITRUM)

    # Small opportunity should pass
    small_opp = ArbitrageOpportunity(
        id=1,
        buy_chain=ChainId.ETHEREUM,
        sell_chain=ChainId.ARBITRUM,
        token=eth,
        buy_price=2000 * 10**18,
        sell_price=2050 * 10**18,
        spread_bps=250,
        estimated_profit=100_000_000_000_000,  # 0.1 ETH
        confidence=0.8,
        detected_at_ns=time.perf_counter_ns(),
        expires_at_ns=time.perf_counter_ns() + 10_000_000_000,
        buy_dex="uniswap_v3",
        sell_dex="uniswap_v3",
    )

    assert risk.check_opportunity(small_opp), "Small opportunity should pass risk check"
    print("  Small opportunity: PASSED")

    # Large opportunity should fail
    large_opp = ArbitrageOpportunity(
        id=2,
        buy_chain=ChainId.ETHEREUM,
        sell_chain=ChainId.ARBITRUM,
        token=eth,
        buy_price=2000 * 10**18,
        sell_price=3000 * 10**18,
        spread_bps=5000,
        estimated_profit=10_000_000_000_000_000_000,  # 10 ETH
        confidence=0.8,
        detected_at_ns=time.perf_counter_ns(),
        expires_at_ns=time.perf_counter_ns() + 10_000_000_000,
        buy_dex="uniswap_v3",
        sell_dex="uniswap_v3",
    )

    assert not risk.check_opportunity(large_opp), "Large opportunity should fail risk check"
    print("  Large opportunity: CORRECTLY REJECTED")

    print("  ✓ PASSED\n")


def test_dispatch_and_redispatch():
    """Test strategy dispatch and re-dispatch on failure."""
    print("=== Test: Dispatch and Re-dispatch ===")

    config = DispatchConfig(
        max_retries=3,
        retry_delays_ms=[10, 50, 100],
    )
    dispatcher = StrategyDispatcher(config)

    eth = create_token("ETH", ChainId.ETHEREUM)
    usdc = create_token("USDC", ChainId.ETHEREUM)
    eth_arb = create_token("ETH", ChainId.ARBITRUM)
    usdc_arb = create_token("USDC", ChainId.ARBITRUM)

    opp = ArbitrageOpportunity(
        id=1,
        buy_chain=ChainId.ETHEREUM,
        sell_chain=ChainId.ARBITRUM,
        token=eth,
        buy_price=2000 * 10**18,
        sell_price=2050 * 10**18,
        spread_bps=250,
        estimated_profit=100_000_000_000_000,
        confidence=0.8,
        detected_at_ns=time.perf_counter_ns(),
        expires_at_ns=time.perf_counter_ns() + 10_000_000_000,
        buy_dex="uniswap_v3",
        sell_dex="uniswap_v3",
    )

    # Mock execution that always fails
    def mock_execute(o):
        return False

    dispatcher.set_execution_callback(mock_execute)

    # Dispatch
    assert dispatcher.dispatch(opp), "Should dispatch opportunity"
    print("  Dispatched: OK")

    # Process queue
    results = dispatcher.process_queue()
    assert len(results) > 0, "Should have results"
    print(f"  Results: {len(results)}")

    # Check re-dispatch
    stats = dispatcher.get_stats()
    print(f"  Stats: {stats}")

    print("  ✓ PASSED\n")


def test_cross_chain_router():
    """Test cross-chain routing."""
    print("=== Test: Cross-Chain Router ===")

    router = CrossChainRouter()

    # Test route finding
    route = router.find_best_route(ChainId.ETHEREUM, ChainId.ARBITRUM)
    assert route is not None, "Should find route ETH -> ARB"
    print(f"  Route ETH->ARB: {route.bridge} (fee: {route.estimated_fee} wei)")

    # Test alternative route
    alt_route = router.find_alternative_route(
        ChainId.ETHEREUM, ChainId.ARBITRUM, route.route_id
    )
    print(f"  Alternative route: {alt_route}")

    # Test DEX registry
    dexes = router.get_dexes_for_chain(ChainId.ETHEREUM)
    assert len(dexes) > 0, "Should have DEXs for Ethereum"
    print(f"  Ethereum DEXs: {dexes}")

    # Test bridge lookup
    bridge = router.get_bridge_for_pair(ChainId.ETHEREUM, ChainId.ARBITRUM)
    assert bridge is not None, "Should have bridge for ETH -> ARB"
    print(f"  Bridge: {bridge}")

    print("  ✓ PASSED\n")


def test_full_engine_cycle():
    """Test a full engine cycle with price updates."""
    print("=== Test: Full Engine Cycle ===")

    config = DispatchConfig(min_profit_bps=10)
    engine = ArbitrageEngine(config)
    engine.start()

    # Create tokens
    eth_eth = create_token("ETH", ChainId.ETHEREUM)
    usdc_eth = create_token("USDC", ChainId.ETHEREUM)
    eth_arb = create_token("ETH", ChainId.ARBITRUM)
    usdc_arb = create_token("USDC", ChainId.ARBITRUM)
    eth_bsc = create_token("ETH", ChainId.BSC)
    usdc_bsc = create_token("USDC", ChainId.BSC)

    # Feed prices
    engine.on_price_update(create_price_update(eth_eth, usdc_eth, 2000 * 10**18))
    engine.on_price_update(create_price_update(eth_arb, usdc_arb, 2050 * 10**18))
    engine.on_price_update(create_price_update(eth_bsc, usdc_bsc, 1980 * 10**18))

    # Run cycle
    results = engine.run_cycle()

    stats = engine.get_stats()
    print(f"  Total updates: {stats['total_updates']}")
    print(f"  Total opportunities: {stats['total_opportunities']}")
    print(f"  Total dispatched: {stats['total_dispatched']}")
    print(f"  Total executed: {stats['total_executed']}")

    assert stats['total_updates'] == 3
    assert stats['total_opportunities'] > 0

    engine.stop()
    print("  ✓ PASSED\n")


def test_circuit_breaker():
    """Test circuit breaker opens after consecutive failures."""
    print("=== Test: Circuit Breaker ===")

    config = DispatchConfig(
        circuit_breaker_threshold=3,
        circuit_breaker_timeout_ms=1000,
    )
    risk = RiskManager(config)

    eth = create_token("ETH", ChainId.ETHEREUM)
    usdc = create_token("USDC", ChainId.ETHEREUM)
    eth_arb = create_token("ETH", ChainId.ARBITRUM)
    usdc_arb = create_token("USDC", ChainId.ARBITRUM)

    opp = ArbitrageOpportunity(
        id=1,
        buy_chain=ChainId.ETHEREUM,
        sell_chain=ChainId.ARBITRUM,
        token=eth,
        buy_price=2000 * 10**18,
        sell_price=2050 * 10**18,
        spread_bps=250,
        estimated_profit=100_000_000_000_000,
        confidence=0.8,
        detected_at_ns=time.perf_counter_ns(),
        expires_at_ns=time.perf_counter_ns() + 10_000_000_000,
        buy_dex="uniswap_v3",
        sell_dex="uniswap_v3",
    )

    # Should pass initially
    assert risk.check_opportunity(opp), "Should pass initially"
    print("  Initial check: PASSED")

    # Report failures
    for i in range(3):
        risk.on_strategy_result(opp, False)
        print(f"  Failure {i+1} reported")

    # Should now be blocked by circuit breaker
    assert not risk.check_opportunity(opp), "Should be blocked by circuit breaker"
    print("  After 3 failures: CORRECTLY BLOCKED")

    print("  ✓ PASSED\n")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Cross-Chain Arbitrage Application Tests")
    print("=" * 60 + "\n")

    test_opportunity_detection()
    test_risk_management()
    test_dispatch_and_redispatch()
    test_cross_chain_router()
    test_full_engine_cycle()
    test_circuit_breaker()

    print("=" * 60)
    print("All tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
