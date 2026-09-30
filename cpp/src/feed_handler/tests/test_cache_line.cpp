#include "feed_handler/cache_line.hpp"

#include <gtest/gtest.h>

using namespace feed_handler;

TEST(CacheLineTest, AlignUp) {
    EXPECT_EQ(align_up(0), 0u);
    EXPECT_EQ(align_up(1), 64u);
    EXPECT_EQ(align_up(63), 64u);
    EXPECT_EQ(align_up(64), 64u);
    EXPECT_EQ(align_up(65), 128u);
    EXPECT_EQ(align_up(128), 128u);
    EXPECT_EQ(align_up(129), 192u);
}

TEST(CacheLineTest, NextPowerOfTwo) {
    EXPECT_EQ(next_power_of_two(0), 1u);
    EXPECT_EQ(next_power_of_two(1), 1u);
    EXPECT_EQ(next_power_of_two(2), 2u);
    EXPECT_EQ(next_power_of_two(3), 4u);
    EXPECT_EQ(next_power_of_two(4), 4u);
    EXPECT_EQ(next_power_of_two(5), 8u);
    EXPECT_EQ(next_power_of_two(1000), 1024u);
    EXPECT_EQ(next_power_of_two(1024), 1024u);
    EXPECT_EQ(next_power_of_two(1025), 2048u);
}

TEST(CacheLineTest, CacheAlignedSize) {
    EXPECT_GE(sizeof(CacheAligned<int>), kCacheLineSize);
}

TEST(CacheLineTest, PrefetchReadDoesNotCrash) {
    int x = 42;
    prefetch_read(&x);
    EXPECT_EQ(x, 42);
}

TEST(CacheLineTest, CompilerBarrierDoesNotCrash) {
    int x = 0;
    compiler_barrier();
    x = 1;
    compiler_barrier();
    EXPECT_EQ(x, 1);
}

TEST(CacheLineTest, MemoryBarrierDoesNotCrash) {
    std::atomic<int> x{0};
    x.store(1, std::memory_order_relaxed);
    memory_barrier();
    EXPECT_EQ(x.load(std::memory_order_relaxed), 1);
}
