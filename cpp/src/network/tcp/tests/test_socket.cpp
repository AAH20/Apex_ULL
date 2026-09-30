#include "network/tcp/socket.hpp"

#include <gtest/gtest.h>
#include <thread>
#include <chrono>

using namespace net;

TEST(SocketTest, CreateAndClose) {
    Socket sock;
    EXPECT_FALSE(sock.valid());
    EXPECT_EQ(sock.fd(), -1);
}

TEST(SocketTest, SetNonblocking) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);
    Socket sock(fd);
    EXPECT_TRUE(sock.valid());
    auto r = sock.set_nonblocking();
    EXPECT_TRUE(r.has_value());
    sock.close();
    EXPECT_FALSE(sock.valid());
}

TEST(SocketTest, SetTcpNodelay) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);
    Socket sock(fd);
    auto r = sock.set_tcp_nodelay(true);
    EXPECT_TRUE(r.has_value());
    sock.close();
}

TEST(SocketTest, SetTcpQuickack) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);
    Socket sock(fd);
    auto r = sock.set_tcp_quickack(true);
    EXPECT_TRUE(r.has_value());
    sock.close();
}

TEST(SocketTest, SetReuseaddr) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);
    Socket sock(fd);
    auto r = sock.set_reuseaddr(true);
    EXPECT_TRUE(r.has_value());
    sock.close();
}

TEST(SocketTest, MoveSemantics) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);
    Socket sock(fd);
    Socket moved = std::move(sock);
    EXPECT_FALSE(sock.valid());
    EXPECT_TRUE(moved.valid());
    moved.close();
}

TEST(SocketTest, BindAndListen) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    ASSERT_GE(fd, 0);
    Socket sock(fd);
    sock.set_reuseaddr(true);

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(0);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    auto r = sock.bind(addr);
    EXPECT_TRUE(r.has_value());
    r = sock.listen(1);
    EXPECT_TRUE(r.has_value());
    sock.close();
}

TEST(SocketTest, SendRecvOnInvalidSocket) {
    Socket sock;
    const char* msg = "test";
    auto r = sock.send(msg, 4);
    EXPECT_FALSE(r.has_value());
    char buf[16];
    auto r2 = sock.recv(buf, sizeof(buf));
    EXPECT_FALSE(r2.has_value());
}
