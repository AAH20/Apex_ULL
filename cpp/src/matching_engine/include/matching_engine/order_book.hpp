#pragma once

#include "matching_engine/types.hpp"

#include <cstdint>
#include <map>
#include <deque>
#include <vector>
#include <optional>

namespace matching_engine {

struct Level {
    Price price{};
    Quantity total_qty{};
    std::deque<OrderId> orders;
};

struct BookLevel {
    Price price{};
    Quantity qty{};
};

class OrderBook {
public:
    void add_order(const Order& order);
    bool cancel_order(OrderId id);
    std::optional<Order> modify_order(OrderId id, Price new_price, Quantity new_qty);

    [[nodiscard]] std::vector<BookLevel> bids(size_t depth = 10) const;
    [[nodiscard]] std::vector<BookLevel> asks(size_t depth = 10) const;
    [[nodiscard]] Price best_bid() const;
    [[nodiscard]] Price best_ask() const;
    [[nodiscard]] Quantity bid_qty_at(Price price) const;
    [[nodiscard]] Quantity ask_qty_at(Price price) const;
    [[nodiscard]] size_t order_count() const noexcept { return order_count_; }
    void clear();

    // Public accessors for MatchingEngine
    auto& bids() noexcept { return bids_; }
    auto& asks() noexcept { return asks_; }
    auto& orders() noexcept { return orders_; }
    const auto& bids() const noexcept { return bids_; }
    const auto& asks() const noexcept { return asks_; }
    const auto& orders() const noexcept { return orders_; }
    void notify_filled() noexcept { --order_count_; }

private:
    struct OrderEntry {
        Price price{};
        Quantity remaining{};
        Side side{Side::Buy};
    };

    std::map<Price, Level, std::greater<Price>> bids_;
    std::map<Price, Level> asks_;
    std::map<OrderId, OrderEntry> orders_;
    size_t order_count_{0};

    void remove_from_level(Level& level, OrderId id);
};

}  // namespace matching_engine
