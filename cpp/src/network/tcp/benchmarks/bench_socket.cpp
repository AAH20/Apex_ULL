#include "network/tcp/socket.hpp"

#include <benchmark/benchmark.h>
#include <thread>

using namespace net;

static void BM_SocketCreate(benchmark::State& state) {
    for (auto _ : state) {
        int fd = ::socket(AF_INET, SOCK_STREAM, 0);
        ::close(fd);
    }
}
BENCHMARK(BM_SocketCreate);

static void BM_SocketSetNonblocking(benchmark::State& state) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    Socket sock(fd);
    for (auto _ : state) {
        sock.set_nonblocking();
    }
    sock.close();
}
BENCHMARK(BM_SocketSetNonblocking);

static void BM_SocketSetTcpNodelay(benchmark::State& state) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    Socket sock(fd);
    for (auto _ : state) {
        sock.set_tcp_nodelay(true);
    }
    sock.close();
}
BENCHMARK(BM_SocketSetTcpNodelay);

static void BM_SocketSetTcpQuickack(benchmark::State& state) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    Socket sock(fd);
    for (auto _ : state) {
        sock.set_tcp_quickack(true);
    }
    sock.close();
}
BENCHMARK(BM_SocketSetTcpQuickack);

static void BM_SocketBindListen(benchmark::State& state) {
    for (auto _ : state) {
        int fd = ::socket(AF_INET, SOCK_STREAM, 0);
        Socket sock(fd);
        sock.set_reuseaddr(true);
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(0);
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        sock.bind(addr);
        sock.listen(128);
        sock.close();
    }
}
BENCHMARK(BM_SocketBindListen);
