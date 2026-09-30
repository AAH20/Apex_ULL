#include "network/udp/udp_socket.hpp"

#include <benchmark/benchmark.h>

using namespace net;

static void BM_UdpSocketCreate(benchmark::State& state) {
    for (auto _ : state) {
        UdpSocket sock;
        sock.create();
    }
}
BENCHMARK(BM_UdpSocketCreate);

static void BM_UdpSocketSetNonblocking(benchmark::State& state) {
    UdpSocket sock;
    sock.create();
    for (auto _ : state) {
        sock.set_nonblocking();
    }
}
BENCHMARK(BM_UdpSocketSetNonblocking);

static void BM_UdpSocketSetReuseAddr(benchmark::State& state) {
    UdpSocket sock;
    sock.create();
    for (auto _ : state) {
        sock.set_reuseaddr(true);
    }
}
BENCHMARK(BM_UdpSocketSetReuseAddr);

static void BM_UdpSocketBind(benchmark::State& state) {
    UdpSocket sock;
    sock.create();
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(0);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    for (auto _ : state) {
        sock.bind(addr);
    }
}
BENCHMARK(BM_UdpSocketBind);

static void BM_UdpSocketConnect(benchmark::State& state) {
    UdpSocket sock;
    sock.create();
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(19096);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    for (auto _ : state) {
        sock.connect(addr);
    }
}
BENCHMARK(BM_UdpSocketConnect);

static void BM_UdpSendTo(benchmark::State& state) {
    UdpSocket sock;
    sock.create();
    sockaddr_in dst{};
    dst.sin_family = AF_INET;
    dst.sin_port = htons(19097);
    dst.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    const char* msg = "benchmark";
    for (auto _ : state) {
        sock.send_to(msg, 10, dst);
    }
}
BENCHMARK(BM_UdpSendTo);
