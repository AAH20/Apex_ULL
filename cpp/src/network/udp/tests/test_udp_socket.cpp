#include "network/udp/udp_socket.hpp"

#include <gtest/gtest.h>

using namespace net;

TEST(UdpSocketTest, CreateAndDestroy) {
    UdpSocket sock;
    auto r = sock.create();
    EXPECT_TRUE(r.has_value());
    EXPECT_TRUE(sock.valid());
    EXPECT_FALSE(sock.connected());
}

TEST(UdpSocketTest, DoubleCreate) {
    UdpSocket sock;
    auto r1 = sock.create();
    EXPECT_TRUE(r1.has_value());
    auto r2 = sock.create();
    EXPECT_TRUE(r2.has_value());
}

TEST(UdpSocketTest, SetNonblocking) {
    UdpSocket sock;
    sock.create();
    auto r = sock.set_nonblocking();
    EXPECT_TRUE(r.has_value());
}

TEST(UdpSocketTest, SetReuseAddr) {
    UdpSocket sock;
    sock.create();
    auto r = sock.set_reuseaddr(true);
    EXPECT_TRUE(r.has_value());
}

TEST(UdpSocketTest, BindToLocal) {
    UdpSocket sock;
    sock.create();
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(0);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    auto r = sock.bind(addr);
    EXPECT_TRUE(r.has_value());
}

TEST(UdpSocketTest, SendWhenNotConnected) {
    UdpSocket sock;
    sock.create();
    auto r = sock.send("test", 4);
    EXPECT_FALSE(r.has_value());
}

TEST(UdpSocketTest, ConnectAndSend) {
    UdpSocket sock;
    sock.create();
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(19090);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    auto r = sock.connect(addr);
    EXPECT_TRUE(r.has_value());
    EXPECT_TRUE(sock.connected());
}

TEST(UdpSocketTest, SendToWithoutConnect) {
    UdpSocket sock;
    sock.create();
    sockaddr_in dst{};
    dst.sin_family = AF_INET;
    dst.sin_port = htons(19091);
    dst.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    auto r = sock.send_to("hello", 5, dst);
    EXPECT_TRUE(r.has_value());
    EXPECT_EQ(r.value(), 5u);
}

TEST(UdpSocketTest, CloseInvalidates) {
    UdpSocket sock;
    sock.create();
    sock.close();
    EXPECT_FALSE(sock.valid());
    EXPECT_FALSE(sock.connected());
}

TEST(UdpSocketTest, MoveSemantics) {
    UdpSocket sock1;
    sock1.create();
    UdpSocket sock2(std::move(sock1));
    EXPECT_TRUE(sock2.valid());
    EXPECT_FALSE(sock1.valid());
}
