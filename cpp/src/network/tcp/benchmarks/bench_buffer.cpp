#include "network/tcp/buffer.hpp"

#include <benchmark/benchmark.h>

using namespace net;

static void BM_BufferAppend(benchmark::State& state) {
    Buffer buf;
    const char* data = "hello world";
    for (auto _ : state) {
        buf.append(data, 11);
        buf.clear();
    }
}
BENCHMARK(BM_BufferAppend);

static void BM_BufferAppendLarge(benchmark::State& state) {
    Buffer buf;
    std::vector<char> data(4096, 'x');
    for (auto _ : state) {
        buf.append(data.data(), data.size());
        buf.clear();
    }
}
BENCHMARK(BM_BufferAppendLarge);

static void BM_BufferConsume(benchmark::State& state) {
    Buffer buf;
    buf.append("hello world", 11);
    for (auto _ : state) {
        buf.consume(5);
        if (buf.size() == 0) buf.append("hello world", 11);
    }
}
BENCHMARK(BM_BufferConsume);

static void BM_BufferDataAccess(benchmark::State& state) {
    Buffer buf;
    buf.append("test data", 9);
    for (auto _ : state) {
        auto span = buf.data();
        benchmark::DoNotOptimize(span.size());
    }
}
BENCHMARK(BM_BufferDataAccess);
