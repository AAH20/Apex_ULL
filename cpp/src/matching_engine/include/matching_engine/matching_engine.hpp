#pragma once

#include "matching_engine/types.hpp"
#include "matching_engine/order_book.hpp"

#include <vector>
#include <cstdint>

namespace matching_engine {

class MatchingEngine {
public:
    void submit(const OrderAction& action);
    void add_order(const Order& order);
    bool cancel_order(OrderId id);

    [[nodiscard]] const OrderBook& book() const noexcept { return book_; }
    [[nodiscard]] const std::vector<Trade>& trades() const noexcept { return trades_; }
    void clear_trades() { trades_.clear(); }

private:
    OrderBook book_;
    std::vector<Trade> trades_;
    uint64_t timestamp_{0};

    void match_buy(Order& order);
    void match_sell(Order& order);
    void execute_trade(OrderId buy_id, OrderId sell_id, Price price, Quantity qty);
};

}  // namespace matching_engine
