#include "network/udp/udp_sender.hpp"

#include <benchmark/benchmark.h>

using namespace net;

static void BM_UdpSenderCreateConnected(benchmark::State& state) {
    UdpSenderConfig config;
    config.use_connected = true;
    for (auto _ : state) {
        UdpSender sender(config);
        sender.initialize();
    }
}
BENCHMARK(BM_UdpSenderCreateConnected);

static void BM_UdpSenderCreateUnconnected(benchmark::State& state) {
    UdpSenderConfig config;
    config.use_connected = false;
    for (auto _ : state) {
        UdpSender sender(config);
        sender.initialize();
    }
}
BENCHMARK(BM_UdpSenderCreateUnconnected);

static void BM_UdpSenderConnect(benchmark::State& state) {
    UdpSenderConfig config;
    config.use_connected = true;
    UdpSender sender(config);
    sender.initialize();
    sockaddr_in peer{};
    peer.sin_family = AF_INET;
    peer.sin_port = htons(19098);
    peer.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    for (auto _ : state) {
        sender.connect(peer);
    }
}
BENCHMARK(BM_UdpSenderConnect);

static void BM_UdpSenderSendConnected(benchmark::State& state) {
    UdpSenderConfig config;
    config.use_connected = true;
    UdpSender sender(config);
    sender.initialize();
    sockaddr_in peer{};
    peer.sin_family = AF_INET;
    peer.sin_port = htons(19099);
    peer.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    sender.connect(peer);
    const char* msg = "bench";
    for (auto _ : state) {
        sender.send(msg, 5);
    }
}
BENCHMARK(BM_UdpSenderSendConnected);

static void BM_UdpSenderSendUnconnected(benchmark::State& state) {
    UdpSenderConfig config;
    config.use_connected = false;
    UdpSender sender(config);
    sender.initialize();
    sockaddr_in peer{};
    peer.sin_family = AF_INET;
    peer.sin_port = htons(19100);
    peer.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    sender.connect(peer);
    const char* msg = "bench";
    for (auto _ : state) {
        sender.send(msg, 5);
    }
}
BENCHMARK(BM_UdpSenderSendUnconnected);

static void BM_UdpSenderSendTo(benchmark::State& state) {
    UdpSenderConfig config;
    config.use_connected = false;
    UdpSender sender(config);
    sender.initialize();
    sockaddr_in dst{};
    dst.sin_family = AF_INET;
    dst.sin_port = htons(19101);
    dst.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    const char* msg = "bench";
    for (auto _ : state) {
        sender.send_to(msg, 5, dst);
    }
}
BENCHMARK(BM_UdpSenderSendTo);
