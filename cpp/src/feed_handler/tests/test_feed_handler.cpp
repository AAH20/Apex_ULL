#include "feed_handler/feed_handler.hpp"

#include <gtest/gtest.h>
#include <chrono>
#include <thread>
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
    append_u64(1000000);  // timestamp
    append_u64(order_id);
    append_u8('B');
    append_u32(shares);
    append_sym(symbol, 8);
    append_u32(price);
    return buf;
}

}  // namespace

TEST(FeedHandlerTest, Initialize) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    EXPECT_TRUE(fh.initialize());
}

TEST(FeedHandlerTest, ProcessPacket) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    ASSERT_TRUE(fh.initialize());

    auto packet = make_add_order_packet(42, "AAPL", 15000, 100);
    auto count = fh.process_packet(packet, 0);
    EXPECT_EQ(count, 1u);

    auto stats = fh.get_stats();
    EXPECT_EQ(stats.messages_parsed, 1u);
}

TEST(FeedHandlerTest, ProcessMultiplePackets) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    ASSERT_TRUE(fh.initialize());

    for (int i = 0; i < 10; ++i) {
        auto packet = make_add_order_packet(i, "AAPL", 15000 + i, 100);
        fh.process_packet(packet, 0);
    }

    auto stats = fh.get_stats();
    EXPECT_EQ(stats.messages_parsed, 10u);
}

TEST(FeedHandlerTest, CallbackInvocation) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    ASSERT_TRUE(fh.initialize());

    int callback_count = 0;
    fh.set_callback([&](const MarketDataMessage& msg, uint64_t) {
        ++callback_count;
        EXPECT_EQ(msg.kind, MarketDataMessage::Kind::AddOrder);
    });

    auto packet = make_add_order_packet(1, "AAPL", 15000, 100);
    fh.process_packet(packet, 0);

    EXPECT_EQ(callback_count, 1);
}

TEST(FeedHandlerTest, StartStop) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    ASSERT_TRUE(fh.initialize());

    EXPECT_TRUE(fh.start());
    EXPECT_TRUE(fh.is_running());

    // Let it run briefly.
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    fh.stop();
    EXPECT_FALSE(fh.is_running());
}

TEST(FeedHandlerTest, StatsTracking) {
    FeedHandlerConfig config;
    config.use_dpdk_stub = true;
    FeedHandler fh(config);
    ASSERT_TRUE(fh.initialize());

    auto packet = make_add_order_packet(1, "AAPL", 15000, 100);
    fh.process_packet(packet, 0);

    auto stats = fh.get_stats();
    EXPECT_EQ(stats.packets_received, 0u);  // Only process_packet was called, not RX path.
    EXPECT_EQ(stats.messages_parsed, 1u);
    EXPECT_EQ(stats.parse_errors, 0u);
}
