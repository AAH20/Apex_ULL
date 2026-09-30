#include "matching_engine/order_book.hpp"
#include <gtest/gtest.h>

using namespace matching_engine;

TEST(OrderBookTest, AddBid) {
    OrderBook book;
    book.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    EXPECT_EQ(book.order_count(), 1u);
    EXPECT_EQ(book.best_bid().raw(), 1000000);
}

TEST(OrderBookTest, AddAsk) {
    OrderBook book;
    book.add_order({OrderId{1}, Side::Sell, OrderType::Limit, Price(101.0), Quantity(5.0), 1});
    EXPECT_EQ(book.order_count(), 1u);
    EXPECT_EQ(book.best_ask().raw(), 1010000);
}

TEST(OrderBookTest, CancelOrder) {
    OrderBook book;
    book.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    EXPECT_TRUE(book.cancel_order(OrderId{1}));
    EXPECT_EQ(book.order_count(), 0u);
    EXPECT_EQ(book.best_bid().raw(), 0);
}

TEST(OrderBookTest, CancelNonExistent) {
    OrderBook book;
    EXPECT_FALSE(book.cancel_order(OrderId{999}));
}

TEST(OrderBookTest, MultipleBidsPricePriority) {
    OrderBook book;
    book.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    book.add_order({OrderId{2}, Side::Buy, OrderType::Limit, Price(101.0), Quantity(5.0), 2});
    book.add_order({OrderId{3}, Side::Buy, OrderType::Limit, Price(99.0), Quantity(20.0), 3});

    EXPECT_EQ(book.best_bid().raw(), 1010000);
    auto levels = book.bids(3);
    ASSERT_EQ(levels.size(), 3u);
    EXPECT_EQ(levels[0].price.raw(), 1010000);
    EXPECT_EQ(levels[1].price.raw(), 1000000);
    EXPECT_EQ(levels[2].price.raw(), 990000);
}

TEST(OrderBookTest, MultipleAsksPricePriority) {
    OrderBook book;
    book.add_order({OrderId{1}, Side::Sell, OrderType::Limit, Price(102.0), Quantity(10.0), 1});
    book.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(101.0), Quantity(5.0), 2});
    book.add_order({OrderId{3}, Side::Sell, OrderType::Limit, Price(103.0), Quantity(20.0), 3});

    EXPECT_EQ(book.best_ask().raw(), 1010000);
    auto levels = book.asks(3);
    ASSERT_EQ(levels.size(), 3u);
    EXPECT_EQ(levels[0].price.raw(), 1010000);
    EXPECT_EQ(levels[1].price.raw(), 1020000);
    EXPECT_EQ(levels[2].price.raw(), 1030000);
}

TEST(OrderBookTest, ModifyOrder) {
    OrderBook book;
    book.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    auto result = book.modify_order(OrderId{1}, Price(105.0), Quantity(8.0));
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(book.best_bid().raw(), 1050000);
    EXPECT_EQ(book.order_count(), 1u);
}

TEST(OrderBookTest, Clear) {
    OrderBook book;
    book.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    book.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(101.0), Quantity(5.0), 2});
    book.clear();
    EXPECT_EQ(book.order_count(), 0u);
    EXPECT_EQ(book.best_bid().raw(), 0);
    EXPECT_EQ(book.best_ask().raw(), 0);
}

TEST(OrderBookTest, BidQtyAt) {
    OrderBook book;
    book.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    book.add_order({OrderId{2}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(5.0), 2});
    EXPECT_EQ(book.bid_qty_at(Price(100.0)).raw(), 150000);
    EXPECT_EQ(book.bid_qty_at(Price(99.0)).raw(), 0);
}
