#pragma once

#include <cstdint>
#include <cstring>
#include <string_view>

namespace feed_handler {

/// Market data message types (ITCH-inspired).
enum class MsgType : uint8_t {
    AddOrder = 'A',
    AddOrderMPID = 'F',
    OrderExecuted = 'E',
    OrderExecutedWithPrice = 'C',
    OrderCancel = 'X',
    OrderDelete = 'D',
    OrderReplace = 'U',
    Trade = 'P',
    CrossTrade = 'Q',
    BrokenTrade = 'B',
    SystemEvent = 'S',
    StockDirectory = 'R',
    StockTradingAction = 'H',
    RegSHORestriction = 'Y',
    MarketPosition = 'L',
    MWCBDecline = 'V',
    MWCBStatus = 'W',
    IPOQuoteUpdate = 'K',
    LULDAuctionCollar = 'J',
    OperationalHalt = 'h',
};

/// Side of an order.
enum class Side : uint8_t {
    Buy = 'B',
    Sell = 'S',
};

/// A timestamp in nanoseconds since midnight UTC.
struct Timestamp {
    uint64_t nanos;

    constexpr Timestamp() noexcept : nanos(0) {}
    constexpr explicit Timestamp(uint64_t ns) noexcept : nanos(ns) {}
};

/// Add-order message (zero-copy view into the packet buffer).
struct AddOrderMsg {
    MsgType type;
    Timestamp timestamp;
    uint64_t order_id;
    Side side;
    uint32_t shares;
    char symbol[8];
    uint32_t price;
};

/// Order-executed message.
struct OrderExecutedMsg {
    MsgType type;
    Timestamp timestamp;
    uint64_t order_id;
    uint32_t shares;
    uint64_t match_id;
};

/// Order-cancel message.
struct OrderCancelMsg {
    MsgType type;
    Timestamp timestamp;
    uint64_t order_id;
    uint32_t shares;
};

/// Order-delete message.
struct OrderDeleteMsg {
    MsgType type;
    Timestamp timestamp;
    uint64_t order_id;
};

/// Order-replace message.
struct OrderReplaceMsg {
    MsgType type;
    Timestamp timestamp;
    uint64_t orig_order_id;
    uint64_t new_order_id;
    uint32_t shares;
    uint32_t price;
};

/// Trade message.
struct TradeMsg {
    MsgType type;
    Timestamp timestamp;
    uint64_t order_id;
    Side side;
    uint32_t shares;
    char symbol[8];
    uint32_t price;
    uint64_t match_id;
};

/// System-event message.
struct SystemEventMsg {
    MsgType type;
    Timestamp timestamp;
    char event_code;
};

/// Union of all message types for ring storage.
struct MarketDataMessage {
    enum class Kind : uint8_t {
        AddOrder,
        OrderExecuted,
        OrderCancel,
        OrderDelete,
        OrderReplace,
        Trade,
        SystemEvent,
        Unknown,
    };

    Kind kind;
    uint64_t timestamp_nanos;
    uint64_t order_id;
    uint64_t aux_id;       // match_id or orig_order_id
    uint32_t shares;
    uint32_t price;
    Side side;
    char symbol[8];
    char event_code;

    MarketDataMessage() noexcept
        : kind(Kind::Unknown), timestamp_nanos(0), order_id(0), aux_id(0),
          shares(0), price(0), side(Side::Buy), symbol{}, event_code(0) {}
};

/// Convert a raw message type byte to enum.
[[nodiscard]] constexpr MsgType to_msg_type(uint8_t c) noexcept {
    return static_cast<MsgType>(c);
}

/// Check if a message type is valid.
[[nodiscard]] constexpr bool is_valid_msg_type(uint8_t c) noexcept {
    switch (static_cast<MsgType>(c)) {
        case MsgType::AddOrder:
        case MsgType::AddOrderMPID:
        case MsgType::OrderExecuted:
        case MsgType::OrderExecutedWithPrice:
        case MsgType::OrderCancel:
        case MsgType::OrderDelete:
        case MsgType::OrderReplace:
        case MsgType::Trade:
        case MsgType::CrossTrade:
        case MsgType::BrokenTrade:
        case MsgType::SystemEvent:
        case MsgType::StockDirectory:
        case MsgType::StockTradingAction:
        case MsgType::RegSHORestriction:
        case MsgType::MarketPosition:
        case MsgType::MWCBDecline:
        case MsgType::MWCBStatus:
        case MsgType::IPOQuoteUpdate:
        case MsgType::LULDAuctionCollar:
        case MsgType::OperationalHalt:
            return true;
        default:
            return false;
    }
}

}  // namespace feed_handler
