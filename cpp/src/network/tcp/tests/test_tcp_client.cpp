#include "network/tcp/tcp_client.hpp"

#include <gtest/gtest.h>
#include <thread>
#include <chrono>

using namespace net;

TEST(TcpClientTest, CreateAndDestroy) {
    ClientConfig config;
    config.host = "127.0.0.1";
    config.port = 19080;

    TcpClient client(config);
    EXPECT_FALSE(client.connected());
}

TEST(TcpClientTest, ConnectToInvalidPort) {
    ClientConfig config;
    config.host = "127.0.0.1";
    config.port = 1;  // Almost certainly nothing listening
    config.timeout_ms = 100;

    TcpClient client(config);
    auto r = client.connect();
    // May succeed or fail depending on OS, but shouldn't crash
    if (r.has_value()) {
        client.disconnect();
    }
}

TEST(TcpClientTest, DoubleConnectFails) {
    ClientConfig config;
    config.host = "127.0.0.1";
    config.port = 19081;

    TcpClient client(config);
    auto r1 = client.connect();
    if (r1.has_value()) {
        auto r2 = client.connect();
        EXPECT_FALSE(r2.has_value());
        client.disconnect();
    }
}

TEST(TcpClientTest, SendWhenDisconnected) {
    ClientConfig config;
    config.host = "127.0.0.1";
    config.port = 19082;

    TcpClient client(config);
    auto r = client.send("test", 4);
    EXPECT_FALSE(r.has_value());
}

TEST(TcpClientTest, DisconnectWhenNotConnected) {
    ClientConfig config;
    config.host = "127.0.0.1";
    config.port = 19083;

    TcpClient client(config);
    client.disconnect();  // Should not crash
    EXPECT_FALSE(client.connected());
}
