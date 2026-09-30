#include "feed_handler/parser.hpp"

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

static void BM_ParseAddOrder(benchmark::State& state) {
    auto packet = make_add_order_packet(42, "AAPL", 15000, 100);
    for (auto _ : state) {
        Parser parser(packet);
        MarketDataMessage msg;
        parser.parse_message(msg);
        benchmark::DoNotOptimize(msg);
    }
}
BENCHMARK(BM_ParseAddOrder);

static void BM_ParseOrderExecuted(benchmark::State& state) {
    std::vector<uint8_t> buf;
    buf.push_back('E');
    for (int i = 7; i >= 0; --i) buf.push_back(static_cast<uint8_t>((999999 >> (i * 8)) & 0xFF));
    for (int i = 7; i >= 0; --i) buf.push_back(static_cast<uint8_t>((0xCAFEBABE >> (i * 8)) & 0xFF));
    buf.push_back(0); buf.push_back(0); buf.push_back(0); buf.push_back(50);
    for (int i = 7; i >= 0; --i) buf.push_back(static_cast<uint8_t>((0x12345678 >> (i * 8)) & 0xFF));

    for (auto _ : state) {
        Parser parser(buf);
        MarketDataMessage msg;
        parser.parse_message(msg);
        benchmark::DoNotOptimize(msg);
    }
}
BENCHMARK(BM_ParseOrderExecuted);

static void BM_ParseTrade(benchmark::State& state) {
    std::vector<uint8_t> buf;
    buf.push_back('P');
    for (int i = 7; i >= 0; --i) buf.push_back(static_cast<uint8_t>((444 >> (i * 8)) & 0xFF));
    for (int i = 7; i >= 0; --i) buf.push_back(static_cast<uint8_t>((0xCAFE0001 >> (i * 8)) & 0xFF));
    buf.push_back('S');
    buf.push_back(0); buf.push_back(0); buf.push_back(1); buf.push_back(244);  // 500
    const char* sym = "MSFT";
    for (int i = 0; i < 8; ++i) buf.push_back(i < 4 ? sym[i] : 0);
    buf.push_back(0); buf.push_back(0); buf.push_back(117); buf.push_back(32);  // 30000
    for (int i = 7; i >= 0; --i) buf.push_back(static_cast<uint8_t>((0x99999999 >> (i * 8)) & 0xFF));

    for (auto _ : state) {
        Parser parser(buf);
        MarketDataMessage msg;
        parser.parse_message(msg);
        benchmark::DoNotOptimize(msg);
    }
}
BENCHMARK(BM_ParseTrade);

static void BM_ParseMultipleMessages(benchmark::State& state) {
    std::vector<uint8_t> buf;
    for (int i = 0; i < 10; ++i) {
        auto pkt = make_add_order_packet(i, "AAPL", 15000 + i, 100);
        buf.insert(buf.end(), pkt.begin(), pkt.end());
    }

    for (auto _ : state) {
        Parser parser(buf);
        MarketDataMessage msg;
        while (parser.has(1)) {
            if (!parser.parse_message(msg)) break;
            benchmark::DoNotOptimize(msg);
        }
    }
}
BENCHMARK(BM_ParseMultipleMessages);
