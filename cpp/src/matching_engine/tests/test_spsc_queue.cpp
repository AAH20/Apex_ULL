#include "matching_engine/spsc_queue.hpp"
#include <gtest/gtest.h>
#include <thread>

using namespace matching_engine;

TEST(SpscQueueTest, BasicPushPop) {
    SpscQueue<int> q(8);
    EXPECT_TRUE(q.empty());
    EXPECT_EQ(q.capacity(), 8u);

    EXPECT_TRUE(q.push(42));
    EXPECT_TRUE(q.push(43));
    EXPECT_EQ(q.size(), 2u);

    auto v1 = q.pop();
    ASSERT_TRUE(v1.has_value());
    EXPECT_EQ(*v1, 42);

    auto v2 = q.pop();
    ASSERT_TRUE(v2.has_value());
    EXPECT_EQ(*v2, 43);

    EXPECT_TRUE(q.empty());
    EXPECT_FALSE(q.pop().has_value());
}

TEST(SpscQueueTest, FullQueue) {
    SpscQueue<int> q(4);
    EXPECT_TRUE(q.push(1));
    EXPECT_TRUE(q.push(2));
    EXPECT_TRUE(q.push(3));
    EXPECT_TRUE(q.push(4));
    EXPECT_TRUE(q.full());
    EXPECT_FALSE(q.push(5));
}

TEST(SpscQueueTest, WrapAround) {
    SpscQueue<int> q(4);
    for (int i = 0; i < 4; ++i) EXPECT_TRUE(q.push(i));
    for (int i = 0; i < 4; ++i) {
        auto v = q.pop();
        ASSERT_TRUE(v.has_value());
        EXPECT_EQ(*v, i);
    }
    for (int i = 10; i < 14; ++i) EXPECT_TRUE(q.push(i));
    for (int i = 10; i < 14; ++i) {
        auto v = q.pop();
        ASSERT_TRUE(v.has_value());
        EXPECT_EQ(*v, i);
    }
}

TEST(SpscQueueTest, PowerOfTwoCapacity) {
    SpscQueue<int> q(5);
    EXPECT_EQ(q.capacity(), 8u);
    SpscQueue<int> q2(100);
    EXPECT_EQ(q2.capacity(), 128u);
}

TEST(SpscQueueTest, SingleProducerSingleConsumer) {
    SpscQueue<uint64_t> q(1024);
    constexpr int kNumItems = 10000;

    std::thread producer([&] {
        for (uint64_t i = 0; i < kNumItems; ++i) {
            while (!q.push(i)) std::this_thread::yield();
        }
    });

    std::thread consumer([&] {
        uint64_t sum = 0;
        for (int i = 0; i < kNumItems; ++i) {
            auto v = q.pop();
            while (!v.has_value()) {
                std::this_thread::yield();
                v = q.pop();
            }
            sum += *v;
        }
        EXPECT_EQ(sum, static_cast<uint64_t>(kNumItems) * (kNumItems - 1) / 2);
    });

    producer.join();
    consumer.join();
}
