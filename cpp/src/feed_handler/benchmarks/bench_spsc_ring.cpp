#include "feed_handler/spsc_ring.hpp"

#include <benchmark/benchmark.h>

using namespace feed_handler;

static void BM_SpscRingPushPop(benchmark::State& state) {
    SpscRing<uint64_t> ring(1024);
    uint64_t i = 0;
    for (auto _ : state) {
        ring.push(i++);
        auto v = ring.pop();
        benchmark::DoNotOptimize(v);
    }
}
BENCHMARK(BM_SpscRingPushPop);

static void BM_SpscRingPushOnly(benchmark::State& state) {
    SpscRing<uint64_t> ring(1024);
    uint64_t i = 0;
    for (auto _ : state) {
        ring.push(i++);
    }
}
BENCHMARK(BM_SpscRingPushOnly);

static void BM_SpscRingPopOnly(benchmark::State& state) {
    SpscRing<uint64_t> ring(1024);
    for (auto _ : state) {
        auto v = ring.pop();
        benchmark::DoNotOptimize(v);
    }
}
BENCHMARK(BM_SpscRingPopOnly);

static void BM_SpscRingSize(benchmark::State& state) {
    SpscRing<uint64_t> ring(1024);
    ring.push(42);
    for (auto _ : state) {
        auto s = ring.size();
        benchmark::DoNotOptimize(s);
    }
}
BENCHMARK(BM_SpscRingSize);
