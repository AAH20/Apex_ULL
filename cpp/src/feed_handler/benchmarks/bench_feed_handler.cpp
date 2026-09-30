#include "feed_handler/feed_handler.hpp"

#include <benchmark/benchmark.h>
#include <cstring>
#include <vector>

using namespace feed_handler;

namespace {

std::vector<uint8_t> make_add_order_packet(uint64_t order_id, const char* symbol,
                                           uint32_t price, uint32_t shares) {
    std::vector<uint8_t> buf;
    auto append_u8 = [&](uint8_t v) { buf.push_back(v); };
    auto append_u32 = [&](uint32_t v) {
        buf.push_back(static_cast<uint8_t>(v >> 24));
        buf.push_back(static_cast<uint8_t>((v >> 16) & 0xFF));
        buf.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
        buf.push_back(static_cast<uint8_t>(v & 0xFF));
    };
    auto append_u64 = [&](uint64_t v) {
        for (int i = 7; i >= 0; --i) buf.push_back(static_cast<uint8_t>((v >> (i * 8)) & 0xFF));
    };
    auto append_sym = [&](const char* s, size_t len) {
        for (size_t i = 0; i < len; ++i) {
            buf.push_back(i < strlen(s) ? static_cast<uint8_t>(s[i]) : 0);
        }
    };

    append_u8('A');
    append_u64(1000000);
    append_u64(order_id);
    append_u8('B');
    append_u32(shares);
    append_sym(symbol, 8);
    append_u32(price);
    return buf;
}

}  // namespace

static void BM_FeedHandlerProcessPacket(benchmark::State& state) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    fh.initialize();

    auto packet = make_add_order_packet(42, "AAPL", 15000, 100);

    for (auto _ : state) {
        fh.process_packet(packet, 0);
    }
}
BENCHMARK(BM_FeedHandlerProcessPacket);

static void BM_FeedHandlerProcessMultiple(benchmark::State& state) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    fh.initialize();

    std::vector<std::vector<uint8_t>> packets;
    for (int i = 0; i < 100; ++i) {
        packets.push_back(make_add_order_packet(i, "AAPL", 15000 + i, 100));
    }

    int idx = 0;
    for (auto _ : state) {
        fh.process_packet(packets[idx], 0);
        idx = (idx + 1) % 100;
    }
}
BENCHMARK(BM_FeedHandlerProcessMultiple);

static void BM_FeedHandlerWithCallback(benchmark::State& state) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    fh.initialize();

    uint64_t count = 0;
    fh.set_callback([&](const MarketDataMessage&, uint64_t) { ++count; });

    auto packet = make_add_order_packet(42, "AAPL", 15000, 100);

    for (auto _ : state) {
        fh.process_packet(packet, 0);
    }
    benchmark::DoNotOptimize(count);
}
BENCHMARK(BM_FeedHandlerWithCallback);

BENCHMARK_MAIN();
