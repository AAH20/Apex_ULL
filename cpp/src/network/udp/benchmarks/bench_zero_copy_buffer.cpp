#include "network/udp/zero_copy_buffer.hpp"

#include <benchmark/benchmark.h>

using namespace net;

static void BM_ZeroCopyBufferCreate(benchmark::State& state) {
    for (auto _ : state) {
        ZeroCopyBuffer buf(2048);
    }
}
BENCHMARK(BM_ZeroCopyBufferCreate);

static void BM_ZeroCopyBufferDataAccess(benchmark::State& state) {
    ZeroCopyBuffer buf(1024);
    for (auto _ : state) {
        auto span = buf.data();
        benchmark::DoNotOptimize(span.data());
    }
}
BENCHMARK(BM_ZeroCopyBufferDataAccess);

static void BM_BufferPoolAcquire(benchmark::State& state) {
    BufferPool pool(2048, 64);
    for (auto _ : state) {
        auto* buf = pool.acquire();
        benchmark::DoNotOptimize(buf);
    }
}
BENCHMARK(BM_BufferPoolAcquire);

static void BM_BufferPoolAcquireRelease(benchmark::State& state) {
    BufferPool pool(2048, 64);
    for (auto _ : state) {
        auto* buf = pool.acquire();
        pool.release(buf);
    }
}
BENCHMARK(BM_BufferPoolAcquireRelease);

static void BM_ZeroCopyBufferSetSize(benchmark::State& state) {
    ZeroCopyBuffer buf(512);
    for (auto _ : state) {
        buf.set_size(256);
    }
}
BENCHMARK(BM_ZeroCopyBufferSetSize);
