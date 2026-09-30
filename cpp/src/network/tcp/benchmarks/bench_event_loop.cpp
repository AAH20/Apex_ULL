#include "network/tcp/event_loop.hpp"

#include <benchmark/benchmark.h>

using namespace net;

static void BM_EventLoopCreate(benchmark::State& state) {
    for (auto _ : state) {
        EventLoop loop;
    }
}
BENCHMARK(BM_EventLoopCreate);

static void BM_EventLoopAddRemove(benchmark::State& state) {
    EventLoop loop;
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    for (auto _ : state) {
        loop.add_fd(fd, EventType::Readable, nullptr);
        loop.remove_fd(fd);
    }
    ::close(fd);
}
BENCHMARK(BM_EventLoopAddRemove);

static void BM_EventLoopPollTimeout(benchmark::State& state) {
    EventLoop loop;
    std::vector<Event> events;
    for (auto _ : state) {
        loop.poll(events, 0);
    }
}
BENCHMARK(BM_EventLoopPollTimeout);

static void BM_EventLoopPollWithFd(benchmark::State& state) {
    EventLoop loop;
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    loop.add_fd(fd, EventType::Readable, nullptr);
    std::vector<Event> events;
    for (auto _ : state) {
        loop.poll(events, 0);
    }
    loop.remove_fd(fd);
    ::close(fd);
}
BENCHMARK(BM_EventLoopPollWithFd);
