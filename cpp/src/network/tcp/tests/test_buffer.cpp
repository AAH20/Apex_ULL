#include "network/tcp/buffer.hpp"

#include <gtest/gtest.h>
#include <cstring>

using namespace net;

TEST(BufferTest, AppendAndSize) {
    Buffer buf;
    EXPECT_TRUE(buf.empty());
    EXPECT_EQ(buf.size(), 0u);

    const char* data = "hello";
    buf.append(data, 5);
    EXPECT_EQ(buf.size(), 5u);
    EXPECT_FALSE(buf.empty());
}

TEST(BufferTest, AppendSpan) {
    Buffer buf;
    std::byte bytes[] = {std::byte{1}, std::byte{2}, std::byte{3}};
    buf.append(std::span(bytes));
    EXPECT_EQ(buf.size(), 3u);
}

TEST(BufferTest, Consume) {
    Buffer buf;
    buf.append("hello world", 11);
    buf.consume(5);
    EXPECT_EQ(buf.size(), 6u);
}

TEST(BufferTest, ConsumeAll) {
    Buffer buf;
    buf.append("test", 4);
    buf.consume(4);
    EXPECT_EQ(buf.size(), 0u);
    EXPECT_TRUE(buf.empty());
}

TEST(BufferTest, Clear) {
    Buffer buf;
    buf.append("data", 4);
    buf.clear();
    EXPECT_EQ(buf.size(), 0u);
    EXPECT_TRUE(buf.empty());
}

TEST(BufferTest, DataAccess) {
    Buffer buf;
    buf.append("abc", 3);
    auto span = buf.data();
    EXPECT_EQ(span.size(), 3u);
    EXPECT_EQ(static_cast<const char*>(static_cast<const void*>(span.data()))[0], 'a');
}

TEST(BufferTest, Writable) {
    Buffer buf(16);
    buf.append("ab", 2);
    auto w = buf.writable();
    EXPECT_EQ(w.size(), 14u);
}

TEST(BufferTest, Reserve) {
    Buffer buf;
    buf.reserve(1024);
    EXPECT_GE(buf.capacity(), 1024u);
}
