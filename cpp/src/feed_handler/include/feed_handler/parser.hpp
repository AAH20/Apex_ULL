#pragma once

#include "market_data.hpp"

#include <cstdint>
#include <cstring>
#include <span>

namespace feed_handler {

/// Zero-copy parser for binary market-data packets.
///
/// Parses directly from a contiguous byte buffer without copying.
/// All multi-byte fields are big-endian (network byte order).
class Parser {
public:
    /// Construct a parser over a byte buffer.
    explicit Parser(std::span<const uint8_t> buffer) noexcept
        : data_(buffer.data()), size_(buffer.size()), pos_(0) {}

    /// Remaining bytes in the buffer.
    [[nodiscard]] std::size_t remaining() const noexcept { return size_ - pos_; }

    /// Current read position.
    [[nodiscard]] std::size_t position() const noexcept { return pos_; }

    /// Check if at least `n` bytes remain.
    [[nodiscard]] bool has(std::size_t n) const noexcept { return remaining() >= n; }

    /// Read a big-endian uint8_t.
    [[nodiscard]] uint8_t read_u8() noexcept {
        return data_[pos_++];
    }

    /// Read a big-endian uint16_t.
    [[nodiscard]] uint16_t read_u16() noexcept {
        uint16_t v;
        std::memcpy(&v, data_ + pos_, 2);
        pos_ += 2;
        return __builtin_bswap16(v);
    }

    /// Read a big-endian uint32_t.
    [[nodiscard]] uint32_t read_u32() noexcept {
        uint32_t v;
        std::memcpy(&v, data_ + pos_, 4);
        pos_ += 4;
        return __builtin_bswap32(v);
    }

    /// Read a big-endian uint64_t.
    [[nodiscard]] uint64_t read_u64() noexcept {
        uint64_t v;
        std::memcpy(&v, data_ + pos_, 8);
        pos_ += 8;
        return __builtin_bswap64(v);
    }

    /// Read a fixed-size string (null-padded).
    void read_symbol(char* dst, std::size_t len) noexcept {
        const auto n = remaining() < len ? remaining() : len;
        std::memcpy(dst, data_ + pos_, n);
        for (std::size_t i = n; i < len; ++i) dst[i] = '\0';
        pos_ += len;
    }

    /// Skip `n` bytes.
    void skip(std::size_t n) noexcept {
        pos_ += n;
        if (pos_ > size_) pos_ = size_;
    }

    /// Parse a complete message from the current position.
    /// Returns true on success, false if the buffer is too short.
    bool parse_message(MarketDataMessage& out) noexcept {
        if (!has(1)) return false;

        const auto type = to_msg_type(read_u8());

        switch (type) {
            case MsgType::AddOrder:
                return parse_add_order(out);
            case MsgType::OrderExecuted:
                return parse_order_executed(out);
            case MsgType::OrderCancel:
                return parse_order_cancel(out);
            case MsgType::OrderDelete:
                return parse_order_delete(out);
            case MsgType::OrderReplace:
                return parse_order_replace(out);
            case MsgType::Trade:
                return parse_trade(out);
            case MsgType::SystemEvent:
                return parse_system_event(out);
            default:
                return false;
        }
    }

private:
    bool parse_add_order(MarketDataMessage& out) noexcept {
        // type(1) + timestamp(8) + order_id(8) + side(1) + shares(4) + symbol(8) + price(4) = 34
        if (!has(33)) return false;
        out.kind = MarketDataMessage::Kind::AddOrder;
        out.timestamp_nanos = read_u64();
        out.order_id = read_u64();
        out.side = static_cast<Side>(read_u8());
        out.shares = read_u32();
        read_symbol(out.symbol, 8);
        out.price = read_u32();
        return true;
    }

    bool parse_order_executed(MarketDataMessage& out) noexcept {
        // type(1) + timestamp(8) + order_id(8) + shares(4) + match_id(8) = 29
        if (!has(28)) return false;
        out.kind = MarketDataMessage::Kind::OrderExecuted;
        out.timestamp_nanos = read_u64();
        out.order_id = read_u64();
        out.shares = read_u32();
        out.aux_id = read_u64();
        return true;
    }

    bool parse_order_cancel(MarketDataMessage& out) noexcept {
        // type(1) + timestamp(8) + order_id(8) + shares(4) = 21
        if (!has(20)) return false;
        out.kind = MarketDataMessage::Kind::OrderCancel;
        out.timestamp_nanos = read_u64();
        out.order_id = read_u64();
        out.shares = read_u32();
        return true;
    }

    bool parse_order_delete(MarketDataMessage& out) noexcept {
        // type(1) + timestamp(8) + order_id(8) = 17
        if (!has(16)) return false;
        out.kind = MarketDataMessage::Kind::OrderDelete;
        out.timestamp_nanos = read_u64();
        out.order_id = read_u64();
        return true;
    }

    bool parse_order_replace(MarketDataMessage& out) noexcept {
        // type(1) + timestamp(8) + orig_id(8) + new_id(8) + shares(4) + price(4) = 33
        if (!has(32)) return false;
        out.kind = MarketDataMessage::Kind::OrderReplace;
        out.timestamp_nanos = read_u64();
        out.aux_id = read_u64();
        out.order_id = read_u64();
        out.shares = read_u32();
        out.price = read_u32();
        return true;
    }

    bool parse_trade(MarketDataMessage& out) noexcept {
        // type(1) + timestamp(8) + order_id(8) + side(1) + shares(4) + symbol(8) + price(4) + match_id(8) = 42
        if (!has(41)) return false;
        out.kind = MarketDataMessage::Kind::Trade;
        out.timestamp_nanos = read_u64();
        out.order_id = read_u64();
        out.side = static_cast<Side>(read_u8());
        out.shares = read_u32();
        read_symbol(out.symbol, 8);
        out.price = read_u32();
        out.aux_id = read_u64();
        return true;
    }

    bool parse_system_event(MarketDataMessage& out) noexcept {
        // type(1) + timestamp(8) + event_code(1) = 10
        if (!has(9)) return false;
        out.kind = MarketDataMessage::Kind::SystemEvent;
        out.timestamp_nanos = read_u64();
        out.event_code = static_cast<char>(read_u8());
        return true;
    }

    const uint8_t* data_;
    std::size_t size_;
    std::size_t pos_;
};

}  // namespace feed_handler
