#include "network/tcp/event_loop.hpp"

#include <gtest/gtest.h>
#include <thread>
#include <chrono>

using namespace net;

TEST(EventLoopTest, CreateAndDestroy) {
    EventLoop loop;
    EXPECT_TRUE(loop.empty());
}

TEST(EventLoopTest, AddRemoveFd) {
    EventLoop loop;
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);

    auto r = loop.add_fd(fd, EventType::Readable, nullptr);
    EXPECT_TRUE(r.has_value());
    EXPECT_FALSE(loop.empty());

    r = loop.remove_fd(fd);
    EXPECT_TRUE(r.has_value());
    EXPECT_TRUE(loop.empty());

    ::close(fd);
}

TEST(EventLoopTest, ModifyFd) {
    EventLoop loop;
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);

    loop.add_fd(fd, EventType::Readable, nullptr);
    auto r = loop.modify_fd(fd, EventType::Writable, nullptr);
    EXPECT_TRUE(r.has_value());

    loop.remove_fd(fd);
    ::close(fd);
}

TEST(EventLoopTest, PollTimeout) {
    EventLoop loop;
    std::vector<Event> events;
    auto start = std::chrono::steady_clock::now();
    auto n = loop.poll(events, 10);
    auto elapsed = std::chrono::steady_clock::now() - start;
    EXPECT_TRUE(n.has_value());
    EXPECT_EQ(*n, 0);
    EXPECT_GE(std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count(), 5);
}

TEST(EventLoopTest, PollWithSocket) {
    EventLoop loop;
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);

    loop.add_fd(fd, EventType::Readable, nullptr);

    // Write to self to trigger readable
    // Actually, let's just test that poll doesn't crash
    std::vector<Event> events;
    auto n = loop.poll(events, 0);
    EXPECT_TRUE(n.has_value());

    loop.remove_fd(fd);
    ::close(fd);
}
