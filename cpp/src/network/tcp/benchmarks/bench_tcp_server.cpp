#include "network/tcp/tcp_server.hpp"

#include <benchmark/benchmark.h>
#include <thread>
#include <chrono>

using namespace net;

static void BM_TcpServerStartStop(benchmark::State& state) {
    for (auto _ : state) {
        ServerConfig config;
        config.port = 0;
        TcpServer server(config);
        server.start();
        server.stop();
    }
}
BENCHMARK(BM_TcpServerStartStop);

static void BM_TcpServerStartOnFixedPort(benchmark::State& state) {
    for (auto _ : state) {
        ServerConfig config;
        config.port = 28080;
        TcpServer server(config);
        server.start();
        server.stop();
    }
}
BENCHMARK(BM_TcpServerStartOnFixedPort);

static void BM_TcpServerBroadcast(benchmark::State& state) {
    ServerConfig config;
    config.port = 0;
    TcpServer server(config);
    server.start();
    const char* msg = "broadcast";
    for (auto _ : state) {
        server.broadcast(msg, 9);
    }
    server.stop();
}
BENCHMARK(BM_TcpServerBroadcast);
