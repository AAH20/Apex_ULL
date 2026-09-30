#include "matching_engine/order_book.hpp"
#include <benchmark/benchmark.h>

using namespace matching_engine;

static void BM_OrderBookAddBid(benchmark::State& state) {
    OrderBook book;
    uint64_t id = 0;
    for (auto _ : state) {
        book.add_order({OrderId{id++}, Side::Buy, OrderType::Limit, Price(100.0 + (id % 10)), Quantity(10.0), id});
        benchmark::DoNotOptimize(book.order_count());
    }
}
BENCHMARK(BM_OrderBookAddBid);

static void BM_OrderBookAddAsk(benchmark::State& state) {
    OrderBook book;
    uint64_t id = 0;
    for (auto _ : state) {
        book.add_order({OrderId{id++}, Side::Sell, OrderType::Limit, Price(101.0 + (id % 10)), Quantity(5.0), id});
        benchmark::DoNotOptimize(book.order_count());
    }
}
BENCHMARK(BM_OrderBookAddAsk);

static void BM_OrderBookCancel(benchmark::State& state) {
    OrderBook book;
    for (uint64_t i = 0; i < 100; ++i) {
        book.add_order({OrderId{i}, Side::Buy, OrderType::Limit, Price(100.0 + (i % 10)), Quantity(10.0), i});
    }
    uint64_t id = 0;
    for (auto _ : state) {
        book.cancel_order(OrderId{id % 100});
        book.add_order({OrderId{id % 100}, Side::Buy, OrderType::Limit, Price(100.0 + (id % 10)), Quantity(10.0), id});
        ++id;
        benchmark::DoNotOptimize(book.order_count());
    }
}
BENCHMARK(BM_OrderBookCancel);

static void BM_OrderBookBestBid(benchmark::State& state) {
    OrderBook book;
    for (uint64_t i = 0; i < 100; ++i) {
        book.add_order({OrderId{i}, Side::Buy, OrderType::Limit, Price(100.0 + (i % 10)), Quantity(10.0), i});
    }
    for (auto _ : state) {
        auto bb = book.best_bid();
        benchmark::DoNotOptimize(bb);
    }
}
BENCHMARK(BM_OrderBookBestBid);

static void BM_OrderBookBestAsk(benchmark::State& state) {
    OrderBook book;
    for (uint64_t i = 0; i < 100; ++i) {
        book.add_order({OrderId{i}, Side::Sell, OrderType::Limit, Price(101.0 + (i % 10)), Quantity(5.0), i});
    }
    for (auto _ : state) {
        auto ba = book.best_ask();
        benchmark::DoNotOptimize(ba);
    }
}
BENCHMARK(BM_OrderBookBestAsk);

static void BM_OrderBookBidsDepth(benchmark::State& state) {
    OrderBook book;
    for (uint64_t i = 0; i < 100; ++i) {
        book.add_order({OrderId{i}, Side::Buy, OrderType::Limit, Price(100.0 + (i % 10)), Quantity(10.0), i});
    }
    for (auto _ : state) {
        auto levels = book.bids(10);
        benchmark::DoNotOptimize(levels.size());
    }
}
BENCHMARK(BM_OrderBookBidsDepth);
