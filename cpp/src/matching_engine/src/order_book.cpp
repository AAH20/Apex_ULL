#include "matching_engine/order_book.hpp"

#include <algorithm>
#include <stdexcept>

namespace matching_engine {

void OrderBook::add_order(const Order& order) {
    if (orders_.contains(order.id)) {
        throw std::invalid_argument("duplicate order ID");
    }
    if (order.qty.raw() <= 0 || order.price.raw() <= 0) {
        throw std::invalid_argument("price and quantity must be positive");
    }
    OrderEntry entry{order.price, order.qty, order.side};
    orders_[order.id] = entry;

    if (order.side == Side::Buy) {
        auto& level = bids_[order.price];
        level.price = order.price;
        level.total_qty = Quantity(level.total_qty.raw() + order.qty.raw());
        level.orders.push_back(order.id);
    } else {
        auto& level = asks_[order.price];
        level.price = order.price;
        level.total_qty = Quantity(level.total_qty.raw() + order.qty.raw());
        level.orders.push_back(order.id);
    }
    ++order_count_;
}

bool OrderBook::cancel_order(OrderId id) {
    auto it = orders_.find(id);
    if (it == orders_.end()) return false;

    if (it->second.side == Side::Buy) {
        auto lit = bids_.find(it->second.price);
        if (lit != bids_.end()) {
            lit->second.total_qty = Quantity(lit->second.total_qty.raw() - it->second.remaining.raw());
            remove_from_level(lit->second, id);
            if (lit->second.orders.empty()) {
                bids_.erase(lit);
            }
        }
    } else {
        auto lit = asks_.find(it->second.price);
        if (lit != asks_.end()) {
            lit->second.total_qty = Quantity(lit->second.total_qty.raw() - it->second.remaining.raw());
            remove_from_level(lit->second, id);
            if (lit->second.orders.empty()) {
                asks_.erase(lit);
            }
        }
    }
    orders_.erase(it);
    --order_count_;
    return true;
}

std::optional<Order> OrderBook::modify_order(OrderId id, Price new_price, Quantity new_qty) {
    auto it = orders_.find(id);
    if (it == orders_.end()) return std::nullopt;

    if (new_price.raw() <= 0 || new_qty.raw() <= 0) {
        throw std::invalid_argument("price and quantity must be positive");
    }
    Order modified{id, it->second.side, OrderType::Limit, new_price, new_qty, 0};
    cancel_order(id);
    add_order(modified);
    return modified;
}

std::vector<BookLevel> OrderBook::bids(size_t depth) const {
    std::vector<BookLevel> result;
    result.reserve(depth);
    for (auto it = bids_.begin(); it != bids_.end() && result.size() < depth; ++it) {
        result.push_back({it->first, it->second.total_qty});
    }
    return result;
}

std::vector<BookLevel> OrderBook::asks(size_t depth) const {
    std::vector<BookLevel> result;
    result.reserve(depth);
    for (auto it = asks_.begin(); it != asks_.end() && result.size() < depth; ++it) {
        result.push_back({it->first, it->second.total_qty});
    }
    return result;
}

Price OrderBook::best_bid() const {
    return bids_.empty() ? Price{} : bids_.begin()->first;
}

Price OrderBook::best_ask() const {
    return asks_.empty() ? Price{} : asks_.begin()->first;
}

Quantity OrderBook::bid_qty_at(Price price) const {
    auto it = bids_.find(price);
    return it == bids_.end() ? Quantity{} : it->second.total_qty;
}

Quantity OrderBook::ask_qty_at(Price price) const {
    auto it = asks_.find(price);
    return it == asks_.end() ? Quantity{} : it->second.total_qty;
}

void OrderBook::clear() {
    bids_.clear();
    asks_.clear();
    orders_.clear();
    order_count_ = 0;
}

void OrderBook::remove_from_level(Level& level, OrderId id) {
    auto it = std::find(level.orders.begin(), level.orders.end(), id);
    if (it != level.orders.end()) {
        level.orders.erase(it);
    }
}

}  // namespace matching_engine
