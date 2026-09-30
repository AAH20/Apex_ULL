#include "feed_handler/parser.hpp"

#include <gtest/gtest.h>
#include <cstring>

using namespace feed_handler;

namespace {

/// Helper: append a big-endian value to a byte vector.
void append_u8(std::vector<uint8_t>& v, uint8_t val) { v.push_back(val); }
void append_u16(std::vector<uint8_t>& v, uint16_t val) {
    v.push_back(static_cast<uint8_t>(val >> 8));
    v.push_back(static_cast<uint8_t>(val & 0xFF));
}
void append_u32(std::vector<uint8_t>& v, uint32_t val) {
    v.push_back(static_cast<uint8_t>(val >> 24));
    v.push_back(static_cast<uint8_t>((val >> 16) & 0xFF));
    v.push_back(static_cast<uint8_t>((val >> 8) & 0xFF));
    v.push_back(static_cast<uint8_t>(val & 0xFF));
}
void append_u64(std::vector<uint8_t>& v, uint64_t val) {
    for (int i = 7; i >= 0; --i) {
        v.push_back(static_cast<uint8_t>((val >> (i * 8)) & 0xFF));
    }
}
void append_symbol(std::vector<uint8_t>& v, const char* sym, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        v.push_back(i < strlen(sym) ? static_cast<uint8_t>(sym[i]) : 0);
    }
}

}  // namespace

TEST(ParserTest, ReadU8) {
    std::vector<uint8_t> buf = {0x42};
    Parser p(buf);
    EXPECT_EQ(p.read_u8(), 0x42u);
    EXPECT_EQ(p.remaining(), 0u);
}

TEST(ParserTest, ReadU16) {
    std::vector<uint8_t> buf = {0xAB, 0xCD};
    Parser p(buf);
    EXPECT_EQ(p.read_u16(), 0xABCDu);
}

TEST(ParserTest, ReadU32) {
    std::vector<uint8_t> buf = {0x12, 0x34, 0x56, 0x78};
    Parser p(buf);
    EXPECT_EQ(p.read_u32(), 0x12345678u);
}

TEST(ParserTest, ReadU64) {
    std::vector<uint8_t> buf = {0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF};
    Parser p(buf);
    EXPECT_EQ(p.read_u64(), 0x0123456789ABCDEFu);
}

TEST(ParserTest, ReadSymbol) {
    std::vector<uint8_t> buf = {'A', 'A', 'P', 'L', 0, 0, 0, 0};
    Parser p(buf);
    char sym[8];
    p.read_symbol(sym, 8);
    EXPECT_STREQ(sym, "AAPL");
}

TEST(ParserTest, ParseAddOrder) {
    std::vector<uint8_t> buf;
    append_u8(buf, 'A');
    append_u64(buf, 1234567890);  // timestamp
    append_u64(buf, 0xDEADBEEF);   // order_id
    append_u8(buf, 'B');           // side
    append_u32(buf, 100);          // shares
    append_symbol(buf, "AAPL", 8);
    append_u32(buf, 15000);        // price

    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_TRUE(p.parse_message(msg));
    EXPECT_EQ(msg.kind, MarketDataMessage::Kind::AddOrder);
    EXPECT_EQ(msg.timestamp_nanos, 1234567890u);
    EXPECT_EQ(msg.order_id, 0xDEADBEEFu);
    EXPECT_EQ(msg.side, Side::Buy);
    EXPECT_EQ(msg.shares, 100u);
    EXPECT_EQ(msg.price, 15000u);
    EXPECT_STREQ(msg.symbol, "AAPL");
}

TEST(ParserTest, ParseOrderExecuted) {
    std::vector<uint8_t> buf;
    append_u8(buf, 'E');
    append_u64(buf, 999999);
    append_u64(buf, 0xCAFEBABE);
    append_u32(buf, 50);
    append_u64(buf, 0x12345678);

    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_TRUE(p.parse_message(msg));
    EXPECT_EQ(msg.kind, MarketDataMessage::Kind::OrderExecuted);
    EXPECT_EQ(msg.timestamp_nanos, 999999u);
    EXPECT_EQ(msg.order_id, 0xCAFEBABEu);
    EXPECT_EQ(msg.shares, 50u);
    EXPECT_EQ(msg.aux_id, 0x12345678u);
}

TEST(ParserTest, ParseOrderCancel) {
    std::vector<uint8_t> buf;
    append_u8(buf, 'X');
    append_u64(buf, 111);
    append_u64(buf, 0xFEEDFACE);
    append_u32(buf, 25);

    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_TRUE(p.parse_message(msg));
    EXPECT_EQ(msg.kind, MarketDataMessage::Kind::OrderCancel);
    EXPECT_EQ(msg.order_id, 0xFEEDFACEu);
    EXPECT_EQ(msg.shares, 25u);
}

TEST(ParserTest, ParseOrderDelete) {
    std::vector<uint8_t> buf;
    append_u8(buf, 'D');
    append_u64(buf, 222);
    append_u64(buf, 0x0BADF00D);

    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_TRUE(p.parse_message(msg));
    EXPECT_EQ(msg.kind, MarketDataMessage::Kind::OrderDelete);
    EXPECT_EQ(msg.order_id, 0x0BADF00Du);
}

TEST(ParserTest, ParseOrderReplace) {
    std::vector<uint8_t> buf;
    append_u8(buf, 'U');
    append_u64(buf, 333);
    append_u64(buf, 0x11111111);  // orig
    append_u64(buf, 0x22222222);  // new
    append_u32(buf, 200);
    append_u32(buf, 16000);

    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_TRUE(p.parse_message(msg));
    EXPECT_EQ(msg.kind, MarketDataMessage::Kind::OrderReplace);
    EXPECT_EQ(msg.aux_id, 0x11111111u);
    EXPECT_EQ(msg.order_id, 0x22222222u);
    EXPECT_EQ(msg.shares, 200u);
    EXPECT_EQ(msg.price, 16000u);
}

TEST(ParserTest, ParseTrade) {
    std::vector<uint8_t> buf;
    append_u8(buf, 'P');
    append_u64(buf, 444);
    append_u64(buf, 0xCAFE0001);
    append_u8(buf, 'S');
    append_u32(buf, 500);
    append_symbol(buf, "MSFT", 8);
    append_u32(buf, 30000);
    append_u64(buf, 0x99999999);

    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_TRUE(p.parse_message(msg));
    EXPECT_EQ(msg.kind, MarketDataMessage::Kind::Trade);
    EXPECT_EQ(msg.order_id, 0xCAFE0001u);
    EXPECT_EQ(msg.side, Side::Sell);
    EXPECT_EQ(msg.shares, 500u);
    EXPECT_STREQ(msg.symbol, "MSFT");
    EXPECT_EQ(msg.price, 30000u);
    EXPECT_EQ(msg.aux_id, 0x99999999u);
}

TEST(ParserTest, ParseSystemEvent) {
    std::vector<uint8_t> buf;
    append_u8(buf, 'S');
    append_u64(buf, 555);
    append_u8(buf, 'O');  // Open

    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_TRUE(p.parse_message(msg));
    EXPECT_EQ(msg.kind, MarketDataMessage::Kind::SystemEvent);
    EXPECT_EQ(msg.event_code, 'O');
}

TEST(ParserTest, ParseMultipleMessages) {
    std::vector<uint8_t> buf;
    // Add order
    append_u8(buf, 'A');
    append_u64(buf, 1000);
    append_u64(buf, 1);
    append_u8(buf, 'B');
    append_u32(buf, 10);
    append_symbol(buf, "IBM", 8);
    append_u32(buf, 10000);
    // Cancel
    append_u8(buf, 'X');
    append_u64(buf, 2000);
    append_u64(buf, 1);
    append_u32(buf, 5);

    Parser p(buf);
    MarketDataMessage msg1, msg2;
    EXPECT_TRUE(p.parse_message(msg1));
    EXPECT_EQ(msg1.kind, MarketDataMessage::Kind::AddOrder);
    EXPECT_TRUE(p.parse_message(msg2));
    EXPECT_EQ(msg2.kind, MarketDataMessage::Kind::OrderCancel);
}

TEST(ParserTest, TruncatedMessage) {
    std::vector<uint8_t> buf;
    append_u8(buf, 'A');
    append_u64(buf, 1000);
    // Missing rest of AddOrder fields.

    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_FALSE(p.parse_message(msg));
}

TEST(ParserTest, EmptyBuffer) {
    std::vector<uint8_t> buf;
    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_FALSE(p.parse_message(msg));
}

TEST(ParserTest, UnknownMessageType) {
    std::vector<uint8_t> buf = {0xFF, 0x00, 0x01};
    Parser p(buf);
    MarketDataMessage msg;
    EXPECT_FALSE(p.parse_message(msg));
}

TEST(ParserTest, IsValidMsgType) {
    EXPECT_TRUE(is_valid_msg_type('A'));
    EXPECT_TRUE(is_valid_msg_type('E'));
    EXPECT_TRUE(is_valid_msg_type('X'));
    EXPECT_TRUE(is_valid_msg_type('D'));
    EXPECT_TRUE(is_valid_msg_type('U'));
    EXPECT_TRUE(is_valid_msg_type('P'));
    EXPECT_TRUE(is_valid_msg_type('S'));
    EXPECT_FALSE(is_valid_msg_type(0));
    EXPECT_FALSE(is_valid_msg_type(0xFF));
}
