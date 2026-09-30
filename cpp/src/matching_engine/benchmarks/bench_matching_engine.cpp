#include "matching_engine/matching_engine.hpp"
#include <benchmark/benchmark.h>

using namespace matching_engine;

static void BM_MatchingEngineSimpleMatch(benchmark::State& state) {
    for (auto _ : state) {
        MatchingEngine engine;
        engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
        engine.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(100.0), Quantity(10.0), 2});
        benchmark::DoNotOptimize(engine.trades().size());
    }
}
BENCHMARK(BM_MatchingEngineSimpleMatch);

static void BM_MatchingEnginePartialFill(benchmark::State& state) {
    for (auto _ : state) {
        MatchingEngine engine;
        engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
        engine.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(100.0), Quantity(4.0), 2});
        benchmark::DoNotOptimize(engine.trades().size());
    }
}
BENCHMARK(BM_MatchingEnginePartialFill);

static void BM_MatchingEngineNoMatch(benchmark::State& state) {
    for (auto _ : state) {
        MatchingEngine engine;
        engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(99.0), Quantity(10.0), 1});
        engine.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(101.0), Quantity(10.0), 2});
        benchmark::DoNotOptimize(engine.book().order_count());
    }
}
BENCHMARK(BM_MatchingEngineNoMatch);

static void BM_MatchingEngineMultipleFills(benchmark::State& state) {
    for (auto _ : state) {
        MatchingEngine engine;
        engine.add_order({OrderId{1}, Side::Sell, OrderType::Limit, Price(100.0), Quantity(3.0), 1});
        engine.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(100.0), Quantity(4.0), 2});
        engine.add_order({OrderId{3}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 3});
        benchmark::DoNotOptimize(engine.trades().size());
    }
}
BENCHMARK(BM_MatchingEngineMultipleFills);

static void BM_MatchingEngineCancel(benchmark::State& state) {
    MatchingEngine engine;
    engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    for (auto _ : state) {
        engine.cancel_order(OrderId{1});
        engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
        benchmark::DoNotOptimize(engine.book().order_count());
    }
}
BENCHMARK(BM_MatchingEngineCancel);
