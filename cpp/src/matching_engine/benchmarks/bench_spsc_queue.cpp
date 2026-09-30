#include "matching_engine/spsc_queue.hpp"
#include <benchmark/benchmark.h>

using namespace matching_engine;

static void BM_SpscQueuePushPop(benchmark::State& state) {
    SpscQueue<uint64_t> q(1024);
    uint64_t i = 0;
    for (auto _ : state) {
        q.push(i++);
        auto v = q.pop();
        benchmark::DoNotOptimize(v);
    }
}
BENCHMARK(BM_SpscQueuePushPop);

static void BM_SpscQueuePushOnly(benchmark::State& state) {
    SpscQueue<uint64_t> q(1024);
    uint64_t i = 0;
    for (auto _ : state) {
        q.push(i++);
    }
}
BENCHMARK(BM_SpscQueuePushOnly);

static void BM_SpscQueuePopOnly(benchmark::State& state) {
    SpscQueue<uint64_t> q(1024);
    for (auto _ : state) {
        auto v = q.pop();
        benchmark::DoNotOptimize(v);
    }
}
BENCHMARK(BM_SpscQueuePopOnly);

static void BM_SpscQueueSize(benchmark::State& state) {
    SpscQueue<uint64_t> q(1024);
    q.push(42);
    for (auto _ : state) {
        auto s = q.size();
        benchmark::DoNotOptimize(s);
    }
}
BENCHMARK(BM_SpscQueueSize);
