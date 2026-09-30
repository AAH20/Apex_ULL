#include "matching_engine/matching_engine.hpp"

#include <algorithm>

namespace matching_engine {

void MatchingEngine::submit(const OrderAction& action) {
    switch (action.action) {
        case Action::New:
            add_order({action.id, action.side, action.type, action.price, action.qty, ++timestamp_});
            break;
        case Action::Cancel:
            cancel_order(action.id);
            break;
        case Action::Modify: {
            auto it = book_.orders().find(action.id);
            if (it != book_.orders().end()) {
                book_.modify_order(action.id, action.price, action.qty);
            }
            break;
        }
    }
}

void MatchingEngine::add_order(const Order& order) {
    Order mutable_order = order;
    if (order.side == Side::Buy) {
        match_buy(mutable_order);
    } else {
        match_sell(mutable_order);
    }
    if (mutable_order.qty.raw() > 0) {
        book_.add_order(mutable_order);
    }
}

bool MatchingEngine::cancel_order(OrderId id) {
    return book_.cancel_order(id);
}

void MatchingEngine::match_buy(Order& order) {
    while (order.qty.raw() > 0) {
        auto& asks = book_.asks();
        if (asks.empty()) break;

        auto best_ask_it = asks.begin();
        if (order.type == OrderType::Limit && order.price < best_ask_it->first) break;

        auto& level = best_ask_it->second;
        while (!level.orders.empty() && order.qty.raw() > 0) {
            OrderId resting_id = level.orders.front();
            auto resting_it = book_.orders().find(resting_id);
            if (resting_it == book_.orders().end()) {
                level.orders.pop_front();
                continue;
            }

            auto& resting = resting_it->second;
            Quantity trade_qty(std::min(order.qty.raw(), resting.remaining.raw()));
            execute_trade(order.id, resting_id, level.price, trade_qty);

            order.qty = Quantity(order.qty.raw() - trade_qty.raw());
            resting.remaining = Quantity(resting.remaining.raw() - trade_qty.raw());
            level.total_qty = Quantity(level.total_qty.raw() - trade_qty.raw());

            if (resting.remaining.raw() == 0) {
                level.orders.pop_front();
                book_.orders().erase(resting_it);
                book_.notify_filled();
            }
        }

        if (level.orders.empty()) {
            asks.erase(best_ask_it);
        }
    }
}

void MatchingEngine::match_sell(Order& order) {
    while (order.qty.raw() > 0) {
        auto& bids = book_.bids();
        if (bids.empty()) break;

        auto best_bid_it = bids.begin();
        if (order.type == OrderType::Limit && order.price > best_bid_it->first) break;

        auto& level = best_bid_it->second;
        while (!level.orders.empty() && order.qty.raw() > 0) {
            OrderId resting_id = level.orders.front();
            auto resting_it = book_.orders().find(resting_id);
            if (resting_it == book_.orders().end()) {
                level.orders.pop_front();
                continue;
            }

            auto& resting = resting_it->second;
            Quantity trade_qty(std::min(order.qty.raw(), resting.remaining.raw()));
            execute_trade(resting_id, order.id, level.price, trade_qty);

            order.qty = Quantity(order.qty.raw() - trade_qty.raw());
            resting.remaining = Quantity(resting.remaining.raw() - trade_qty.raw());
            level.total_qty = Quantity(level.total_qty.raw() - trade_qty.raw());

            if (resting.remaining.raw() == 0) {
                level.orders.pop_front();
                book_.orders().erase(resting_it);
                book_.notify_filled();
            }
        }

        if (level.orders.empty()) {
            bids.erase(best_bid_it);
        }
    }
}

void MatchingEngine::execute_trade(OrderId buy_id, OrderId sell_id, Price price, Quantity qty) {
    trades_.push_back({buy_id, sell_id, price, qty, ++timestamp_});
}

}  // namespace matching_engine
