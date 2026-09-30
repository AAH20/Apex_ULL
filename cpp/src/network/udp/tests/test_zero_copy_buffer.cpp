#include "network/udp/zero_copy_buffer.hpp"

#include <gtest/gtest.h>

using namespace net;

TEST(ZeroCopyBufferTest, CreateWithCapacity) {
    ZeroCopyBuffer buf(1024);
    EXPECT_EQ(buf.capacity(), 1024u);
    EXPECT_EQ(buf.size(), 0u);
}

TEST(ZeroCopyBufferTest, DataSpan) {
    ZeroCopyBuffer buf(256);
    auto span = buf.data();
    EXPECT_EQ(span.size(), 256u);
}

TEST(ZeroCopyBufferTest, SetSize) {
    ZeroCopyBuffer buf(512);
    buf.set_size(100);
    EXPECT_EQ(buf.size(), 100u);
}

TEST(ZeroCopyBufferTest, Reset) {
    ZeroCopyBuffer buf(128);
    buf.set_size(64);
    buf.reset();
    EXPECT_EQ(buf.size(), 0u);
}

TEST(BufferPoolTest, CreatePool) {
    BufferPool pool(1024, 16);
    EXPECT_EQ(pool.buffer_size(), 1024u);
    EXPECT_EQ(pool.pool_size(), 16u);
    EXPECT_EQ(pool.available(), 16u);
}

TEST(BufferPoolTest, AcquireRelease) {
    BufferPool pool(512, 4);
    auto* buf = pool.acquire();
    EXPECT_NE(buf, nullptr);
    EXPECT_EQ(pool.available(), 3u);
    pool.release(buf);
    EXPECT_EQ(pool.available(), 4u);
}

TEST(BufferPoolTest, AcquireExhausts) {
    BufferPool pool(256, 2);
    auto* b1 = pool.acquire();
    auto* b2 = pool.acquire();
    auto* b3 = pool.acquire();
    EXPECT_NE(b1, nullptr);
    EXPECT_NE(b2, nullptr);
    EXPECT_EQ(b3, nullptr);
}

TEST(BufferPoolTest, AcquiredBufferUsable) {
    BufferPool pool(128, 1);
    auto* buf = pool.acquire();
    ASSERT_NE(buf, nullptr);
    auto span = buf->data();
    EXPECT_EQ(span.size(), 128u);
    buf->set_size(64);
    EXPECT_EQ(buf->size(), 64u);
}
