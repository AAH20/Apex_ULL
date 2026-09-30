"""
Demo: Cross-Chain Arbitrage Engine
===================================

Demonstrates the full cross-chain arbitrage pipeline with
simulated price feeds and strategy execution.
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
    DispatchConfig,
)


def create_token(symbol: str, chain_id: ChainId) -> Token:
    """Create a token."""
    return Token(
        address=f"0x{symbol.lower()}_{int(chain_id):04x}",
        symbol=symbol,
        decimals=18,
        chain_id=chain_id,
        is_stable=symbol in ("USDC", "USDT", "DAI"),
    )


def create_price_update(
    token_in: Token,
    token_out: Token,
    price: int,
    dex_id: str = "uniswap_v3",
) -> PriceUpdate:
    """Create a price update."""
    return PriceUpdate(
        token_in=token_in,
        token_out=token_out,
        price=price,
        liquidity=10_000_000_000_000_000_000,
        timestamp_ns=time.perf_counter_ns(),
        dex_id=dex_id,
        block_number=1000,
    )


def run_demo():
    """Run the demo."""
    print("\n" + "=" * 70)
    print("Cross-Chain Arbitrage Engine Demo")
    print("=" * 70 + "\n")

    # Configuration
    config = DispatchConfig(
        min_profit_bps=20,
        max_retries=3,
        retry_delays_ms=[100, 500, 2000],
        max_position_size=5_000_000_000_000_000_000,
        max_daily_volume=50_000_000_000_000_000_000,
    )

    engine = ArbitrageEngine(config)
    engine.start()

    # Create tokens for each chain
    tokens = {}
    for chain in [ChainId.ETHEREUM, ChainId.ARBITRUM, ChainId.BSC, ChainId.POLYGON]:
        eth = create_token("ETH", chain)
        usdc = create_token("USDC", chain)
        tokens[chain] = (eth, usdc)

    print("Phase 1: Feeding initial prices...")
    print("-" * 40)

    # Base prices (USDC per ETH)
    base_prices = {
        ChainId.ETHEREUM: 2000,
        ChainId.ARBITRUM: 2005,
        ChainId.BSC: 1995,
        ChainId.POLYGON: 2002,
    }

    for chain, (eth, usdc) in tokens.items():
        price = base_prices[chain] * 10**18
        engine.on_price_update(create_price_update(eth, usdc, price))
        print(f"  {chain.name}: {base_prices[chain]} USDC/ETH")

    # Run first cycle
    print("\nPhase 2: Running arbitrage cycle...")
    print("-" * 40)
    results = engine.run_cycle()

    stats = engine.get_stats()
    print(f"  Opportunities found: {stats['total_opportunities']}")
    print(f"  Strategies dispatched: {stats['total_dispatched']}")
    print(f"  Strategies executed: {stats['total_executed']}")

    # Simulate price movement creating arbitrage
    print("\nPhase 3: Simulating price movement...")
    print("-" * 40)

    # Arbitrum price spikes
    eth_arb, usdc_arb = tokens[ChainId.ARBITRUM]
    engine.on_price_update(create_price_update(eth_arb, usdc_arb, 2100 * 10**18))
    print("  Arbitrum ETH price spikes to 2100 USDC")

    # BSC price drops
    eth_bsc, usdc_bsc = tokens[ChainId.BSC]
    engine.on_price_update(create_price_update(eth_bsc, usdc_bsc, 1950 * 10**18))
    print("  BSC ETH price drops to 1950 USDC")

    # Run more cycles
    print("\nPhase 4: Running more cycles...")
    print("-" * 40)

    for i in range(5):
        # Add some random noise to prices
        for chain, (eth, usdc) in tokens.items():
            noise = random.randint(-20, 20)
            price = (base_prices[chain] + noise) * 10**18
            engine.on_price_update(create_price_update(eth, usdc, price))

        results = engine.run_cycle()
        stats = engine.get_stats()
        print(f"  Cycle {i+1}: {stats['total_opportunities']} opportunities, "
              f"{stats['total_dispatched']} dispatched, "
              f"{stats['total_executed']} executed")

    # Final stats
    print("\n" + "=" * 70)
    print("Final Statistics")
    print("=" * 70)

    stats = engine.get_stats()
    print(f"  Total price updates: {stats['total_updates']}")
    print(f"  Total opportunities: {stats['total_opportunities']}")
    print(f"  Total dispatched: {stats['total_dispatched']}")
    print(f"  Total executed: {stats['total_executed']}")
    print(f"  Total profit: {stats['total_profit']} wei")
    print(f"  Detector stats: {stats['detector']}")
    print(f"  Dispatcher stats: {stats['dispatcher']}")
    print(f"  Risk stats: {stats['risk']}")

    engine.stop()
    print("\nDemo complete!")


if __name__ == "__main__":
    run_demo()
