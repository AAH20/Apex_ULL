#include "matching_engine/matching_engine.hpp"
#include <gtest/gtest.h>

using namespace matching_engine;

TEST(MatchingEngineTest, SimpleMatch) {
    MatchingEngine engine;
    engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    engine.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(100.0), Quantity(10.0), 2});

    EXPECT_EQ(engine.book().order_count(), 0u);
    EXPECT_EQ(engine.trades().size(), 1u);
    EXPECT_EQ(engine.trades()[0].buy_id.value, 1u);
    EXPECT_EQ(engine.trades()[0].sell_id.value, 2u);
    EXPECT_EQ(engine.trades()[0].price.raw(), 1000000);
    EXPECT_EQ(engine.trades()[0].qty.raw(), 100000);
}

TEST(MatchingEngineTest, PartialFill) {
    MatchingEngine engine;
    engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    engine.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(100.0), Quantity(4.0), 2});

    EXPECT_EQ(engine.book().order_count(), 1u);
    EXPECT_EQ(engine.trades().size(), 1u);
    EXPECT_EQ(engine.trades()[0].qty.raw(), 40000);
    EXPECT_EQ(engine.book().best_bid().raw(), 1000000);
}

TEST(MatchingEngineTest, NoMatchSpread) {
    MatchingEngine engine;
    engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(99.0), Quantity(10.0), 1});
    engine.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(101.0), Quantity(10.0), 2});

    EXPECT_EQ(engine.book().order_count(), 2u);
    EXPECT_EQ(engine.trades().size(), 0u);
}

TEST(MatchingEngineTest, PricePriority) {
    MatchingEngine engine;
    engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(99.0), Quantity(5.0), 1});
    engine.add_order({OrderId{2}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(5.0), 2});
    engine.add_order({OrderId{3}, Side::Sell, OrderType::Limit, Price(99.0), Quantity(7.0), 3});

    ASSERT_GE(engine.trades().size(), 1u);
    EXPECT_EQ(engine.trades()[0].price.raw(), 1000000);
    EXPECT_EQ(engine.trades()[0].qty.raw(), 50000);
}

TEST(MatchingEngineTest, CancelOrder) {
    MatchingEngine engine;
    engine.add_order({OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 1});
    EXPECT_TRUE(engine.cancel_order(OrderId{1}));
    EXPECT_EQ(engine.book().order_count(), 0u);
}

TEST(MatchingEngineTest, SubmitNew) {
    MatchingEngine engine;
    engine.submit({Action::New, OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0)});
    EXPECT_EQ(engine.book().order_count(), 1u);
}

TEST(MatchingEngineTest, SubmitCancel) {
    MatchingEngine engine;
    engine.submit({Action::New, OrderId{1}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0)});
    engine.submit({Action::Cancel, OrderId{1}});
    EXPECT_EQ(engine.book().order_count(), 0u);
}

TEST(MatchingEngineTest, MultipleFills) {
    MatchingEngine engine;
    engine.add_order({OrderId{1}, Side::Sell, OrderType::Limit, Price(100.0), Quantity(3.0), 1});
    engine.add_order({OrderId{2}, Side::Sell, OrderType::Limit, Price(100.0), Quantity(4.0), 2});
    engine.add_order({OrderId{3}, Side::Buy, OrderType::Limit, Price(100.0), Quantity(10.0), 3});

    EXPECT_EQ(engine.trades().size(), 2u);
    EXPECT_EQ(engine.book().order_count(), 1u);
    EXPECT_EQ(engine.book().best_bid().raw(), 1000000);
}
