#include "network/udp/udp_sender.hpp"

#include <gtest/gtest.h>

using namespace net;

TEST(UdpSenderTest, CreateConnected) {
    UdpSenderConfig config;
    config.use_connected = true;
    UdpSender sender(config);
    auto r = sender.initialize();
    EXPECT_TRUE(r.has_value());
    EXPECT_TRUE(sender.fd() >= 0);
}

TEST(UdpSenderTest, CreateUnconnected) {
    UdpSenderConfig config;
    config.use_connected = false;
    UdpSender sender(config);
    auto r = sender.initialize();
    EXPECT_TRUE(r.has_value());
}

TEST(UdpSenderTest, ConnectAndSendConnected) {
    UdpSenderConfig config;
    config.use_connected = true;
    UdpSender sender(config);
    sender.initialize();

    sockaddr_in peer{};
    peer.sin_family = AF_INET;
    peer.sin_port = htons(19092);
    peer.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    auto r = sender.connect(peer);
    EXPECT_TRUE(r.has_value());
    EXPECT_TRUE(sender.connected());

    auto sr = sender.send("ping", 4);
    EXPECT_TRUE(sr.has_value());
}

TEST(UdpSenderTest, SendUnconnected) {
    UdpSenderConfig config;
    config.use_connected = false;
    UdpSender sender(config);
    sender.initialize();

    sockaddr_in peer{};
    peer.sin_family = AF_INET;
    peer.sin_port = htons(19093);
    peer.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    sender.connect(peer);

    auto r = sender.send("data", 4);
    EXPECT_TRUE(r.has_value());
}

TEST(UdpSenderTest, SendToUnconnected) {
    UdpSenderConfig config;
    config.use_connected = false;
    UdpSender sender(config);
    sender.initialize();

    sockaddr_in dst{};
    dst.sin_family = AF_INET;
    dst.sin_port = htons(19094);
    dst.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    auto r = sender.send_to("msg", 3, dst);
    EXPECT_TRUE(r.has_value());
}

TEST(UdpSenderTest, BufferPoolAccessible) {
    UdpSenderConfig config;
    config.buffer_pool_size = 8;
    config.buffer_size = 512;
    UdpSender sender(config);
    auto& pool = sender.buffer_pool();
    EXPECT_EQ(pool.pool_size(), 8u);
    EXPECT_EQ(pool.buffer_size(), 512u);
}

TEST(UdpSenderTest, SendSpan) {
    UdpSenderConfig config;
    config.use_connected = true;
    UdpSender sender(config);
    sender.initialize();

    sockaddr_in peer{};
    peer.sin_family = AF_INET;
    peer.sin_port = htons(19095);
    peer.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    sender.connect(peer);

    std::array<std::byte, 4> data{};
    auto r = sender.send(std::span<const std::byte>(data));
    EXPECT_TRUE(r.has_value());
}
