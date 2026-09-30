#include "matching_engine/types.hpp"
#include <gtest/gtest.h>

using namespace matching_engine;

TEST(PriceTest, Construction) {
    Price p(100.50);
    EXPECT_EQ(p.raw(), 1005000);
    EXPECT_DOUBLE_EQ(p.to_double(), 100.50);
}

TEST(PriceTest, Arithmetic) {
    Price a(10.25);
    Price b(5.75);
    EXPECT_EQ((a + b).raw(), 160000);
    EXPECT_EQ((a - b).raw(), 45000);
}

TEST(PriceTest, Comparison) {
    Price a(100.0);
    Price b(200.0);
    EXPECT_TRUE(a < b);
    EXPECT_TRUE(b > a);
    EXPECT_TRUE(a == Price(100.0));
    EXPECT_TRUE(a != b);
}

TEST(PriceTest, Negative) {
    Price p(-50.25);
    EXPECT_EQ(p.raw(), -502500);
    EXPECT_DOUBLE_EQ(p.to_double(), -50.25);
}

TEST(QuantityTest, Construction) {
    Quantity q(1000.5);
    EXPECT_EQ(q.raw(), 10005000);
    EXPECT_DOUBLE_EQ(q.to_double(), 1000.5);
}

TEST(QuantityTest, Arithmetic) {
    Quantity a(100.0);
    Quantity b(30.0);
    EXPECT_EQ((a - b).raw(), 700000);
    EXPECT_TRUE(a > b);
    EXPECT_TRUE(b < a);
}

TEST(QuantityTest, Zero) {
    Quantity q;
    EXPECT_EQ(q.raw(), 0);
    EXPECT_DOUBLE_EQ(q.to_double(), 0.0);
}

TEST(TypesTest, OrderIdComparison) {
    OrderId a{100};
    OrderId b{200};
    EXPECT_TRUE(a < b);
    EXPECT_TRUE(a == OrderId{100});
    EXPECT_TRUE(a != b);
}
