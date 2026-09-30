#include "network/tcp/tcp_server.hpp"

#include <gtest/gtest.h>
#include <thread>
#include <chrono>

using namespace net;

TEST(TcpServerTest, StartStop) {
    ServerConfig config;
    config.port = 0;  // Let OS choose
    config.tcp_nodelay = true;
    config.tcp_quickack = true;

    TcpServer server(config);
    auto r = server.start();
    EXPECT_TRUE(r.has_value());
    EXPECT_TRUE(server.running());

    server.stop();
    EXPECT_FALSE(server.running());
}

TEST(TcpServerTest, StartOnFixedPort) {
    ServerConfig config;
    config.port = 18080;
    config.tcp_nodelay = true;
    config.tcp_quickack = true;

    TcpServer server(config);
    auto r = server.start();
    EXPECT_TRUE(r.has_value());
    EXPECT_TRUE(server.running());

    server.stop();
}

TEST(TcpServerTest, DoubleStartFails) {
    ServerConfig config;
    config.port = 18081;

    TcpServer server(config);
    auto r1 = server.start();
    EXPECT_TRUE(r1.has_value());

    auto r2 = server.start();
    EXPECT_FALSE(r2.has_value());

    server.stop();
}

TEST(TcpServerTest, SendOnInvalidFd) {
    ServerConfig config;
    config.port = 18082;

    TcpServer server(config);
    auto r = server.send(-1, "test", 4);
    EXPECT_FALSE(r.has_value());
}

TEST(TcpServerTest, BroadcastEmpty) {
    ServerConfig config;
    config.port = 18083;

    TcpServer server(config);
    auto r = server.broadcast("test", 4);
    EXPECT_TRUE(r.has_value());
}
