#include "feed_handler/spsc_ring.hpp"

#include <gtest/gtest.h>
#include <thread>
#include <vector>

using namespace feed_handler;

TEST(SpscRingTest, BasicPushPop) {
    SpscRing<int> ring(8);

    EXPECT_TRUE(ring.empty());
    EXPECT_FALSE(ring.full());
    EXPECT_EQ(ring.size(), 0u);
    EXPECT_EQ(ring.capacity(), 8u);

    EXPECT_TRUE(ring.push(42));
    EXPECT_TRUE(ring.push(43));
    EXPECT_EQ(ring.size(), 2u);

    auto v1 = ring.pop();
    ASSERT_TRUE(v1.has_value());
    EXPECT_EQ(*v1, 42);

    auto v2 = ring.pop();
    ASSERT_TRUE(v2.has_value());
    EXPECT_EQ(*v2, 43);

    EXPECT_TRUE(ring.empty());
    EXPECT_FALSE(ring.pop().has_value());
}

TEST(SpscRingTest, CapacityIsPowerOfTwo) {
    SpscRing<int> ring(5);
    EXPECT_EQ(ring.capacity(), 8u);

    SpscRing<int> ring2(100);
    EXPECT_EQ(ring2.capacity(), 128u);
}

TEST(SpscRingTest, FullRing) {
    SpscRing<int> ring(4);

    EXPECT_TRUE(ring.push(1));
    EXPECT_TRUE(ring.push(2));
    EXPECT_TRUE(ring.push(3));
    EXPECT_TRUE(ring.push(4));
    EXPECT_TRUE(ring.full());
    EXPECT_FALSE(ring.push(5));

    EXPECT_EQ(ring.size(), 4u);
}

TEST(SpscRingTest, WrapAround) {
    SpscRing<int> ring(4);

    // Fill, drain, fill again to test wrap-around.
    for (int i = 0; i < 4; ++i) EXPECT_TRUE(ring.push(i));
    for (int i = 0; i < 4; ++i) {
        auto v = ring.pop();
        ASSERT_TRUE(v.has_value());
        EXPECT_EQ(*v, i);
    }

    for (int i = 10; i < 14; ++i) EXPECT_TRUE(ring.push(i));
    for (int i = 10; i < 14; ++i) {
        auto v = ring.pop();
        ASSERT_TRUE(v.has_value());
        EXPECT_EQ(*v, i);
    }
}

TEST(SpscRingTest, Peek) {
    SpscRing<int> ring(4);

    EXPECT_EQ(ring.peek(), nullptr);

    ring.push(99);
    const int* p = ring.peek();
    ASSERT_NE(p, nullptr);
    EXPECT_EQ(*p, 99);

    // Peek doesn't remove.
    EXPECT_EQ(ring.size(), 1u);
    ring.pop();
    EXPECT_EQ(ring.peek(), nullptr);
}

TEST(SpscRingTest, MoveOnlyType) {
    SpscRing<std::unique_ptr<int>> ring(4);

    auto ptr = std::make_unique<int>(42);
    EXPECT_TRUE(ring.push(std::move(ptr)));

    auto result = ring.pop();
    ASSERT_TRUE(result.has_value());
    EXPECT_NE(*result, nullptr);
    EXPECT_EQ(**result, 42);
}

TEST(SpscRingTest, SingleProducerSingleConsumer) {
    SpscRing<uint64_t> ring(1024);
    constexpr int kNumItems = 10000;

    std::thread producer([&] {
        for (uint64_t i = 0; i < kNumItems; ++i) {
            while (!ring.push(i)) {
                std::this_thread::yield();
            }
        }
    });

    std::thread consumer([&] {
        uint64_t sum = 0;
        for (int i = 0; i < kNumItems; ++i) {
            auto v = ring.pop();
            while (!v.has_value()) {
                std::this_thread::yield();
                v = ring.pop();
            }
            sum += *v;
        }
        EXPECT_EQ(sum, static_cast<uint64_t>(kNumItems) * (kNumItems - 1) / 2);
    });

    producer.join();
    consumer.join();
}
