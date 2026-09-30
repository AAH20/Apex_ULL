#include "network/tcp/event_loop.hpp"

#include <cstring>

#if defined(__linux__)
    #include <sys/epoll.h>
#elif defined(__APPLE__)
    #include <sys/event.h>
#endif

namespace net {

EventLoop::EventLoop() {
#if defined(__linux__)
    epoll_fd_ = ::epoll_create1(EPOLL_CLOEXEC);
#elif defined(__APPLE__)
    kqueue_fd_ = ::kqueue();
#endif
}

EventLoop::~EventLoop() noexcept {
#if defined(__linux__)
    if (epoll_fd_ >= 0) ::close(epoll_fd_);
#elif defined(__APPLE__)
    if (kqueue_fd_ >= 0) ::close(kqueue_fd_);
#endif
}

std::expected<void, std::error_code> EventLoop::add_fd(int fd, EventType mask, void* user_data) noexcept {
#if defined(__linux__)
    epoll_event ev{};
    ev.events = EPOLLET;
    if (mask & EventType::Readable) ev.events |= EPOLLIN;
    if (mask & EventType::Writable) ev.events |= EPOLLOUT;
    ev.data.ptr = user_data;
    if (::epoll_ctl(epoll_fd_, EPOLL_CTL_ADD, fd, &ev) < 0)
        return std::unexpected(std::error_code(errno, std::generic_category()));
#elif defined(__APPLE__)
    struct kevent changes[2];
    int n = 0;
    if (mask & EventType::Readable) {
        EV_SET(&changes[n++], fd, EVFILT_READ, EV_ADD | EV_CLEAR, 0, 0, user_data);
    }
    if (mask & EventType::Writable) {
        EV_SET(&changes[n++], fd, EVFILT_WRITE, EV_ADD | EV_CLEAR, 0, 0, user_data);
    }
    if (::kevent(kqueue_fd_, changes, n, nullptr, 0, nullptr) < 0)
        return std::unexpected(std::error_code(errno, std::generic_category()));
#endif
    handlers_[fd] = {mask, user_data};
    return {};
}

std::expected<void, std::error_code> EventLoop::modify_fd(int fd, EventType mask, void* user_data) noexcept {
#if defined(__linux__)
    epoll_event ev{};
    ev.events = EPOLLET;
    if (mask & EventType::Readable) ev.events |= EPOLLIN;
    if (mask & EventType::Writable) ev.events |= EPOLLOUT;
    ev.data.ptr = user_data;
    if (::epoll_ctl(epoll_fd_, EPOLL_CTL_MOD, fd, &ev) < 0)
        return std::unexpected(std::error_code(errno, std::generic_category()));
#elif defined(__APPLE__)
    // kqueue: remove then re-add for simplicity
    remove_fd(fd);
    return add_fd(fd, mask, user_data);
#endif
    handlers_[fd] = {mask, user_data};
    return {};
}

std::expected<void, std::error_code> EventLoop::remove_fd(int fd) noexcept {
#if defined(__linux__)
    if (::epoll_ctl(epoll_fd_, EPOLL_CTL_DEL, fd, nullptr) < 0)
        return std::unexpected(std::error_code(errno, std::generic_category()));
#elif defined(__APPLE__)
    struct kevent changes[2];
    int n = 0;
    EV_SET(&changes[n++], fd, EVFILT_READ, EV_DELETE, 0, 0, nullptr);
    EV_SET(&changes[n++], fd, EVFILT_WRITE, EV_DELETE, 0, 0, nullptr);
    ::kevent(kqueue_fd_, changes, n, nullptr, 0, nullptr);
#endif
    handlers_.erase(fd);
    return {};
}

std::expected<int, std::error_code> EventLoop::poll(std::vector<Event>& events, int timeout_ms) noexcept {
    events.clear();
#if defined(__linux__)
    epoll_event evs[1024];
    int n = ::epoll_wait(epoll_fd_, evs, 1024, timeout_ms);
    if (n < 0) {
        if (errno == EINTR) return 0;
        return std::unexpected(std::error_code(errno, std::generic_category()));
    }
    events.reserve(n);
    for (int i = 0; i < n; ++i) {
        EventType type{};
        if (evs[i].events & EPOLLIN) type = static_cast<EventType>(static_cast<uint8_t>(type) | static_cast<uint8_t>(EventType::Readable));
        if (evs[i].events & EPOLLOUT) type = static_cast<EventType>(static_cast<uint8_t>(type) | static_cast<uint8_t>(EventType::Writable));
        if (evs[i].events & (EPOLLERR | EPOLLHUP)) type = static_cast<EventType>(static_cast<uint8_t>(type) | static_cast<uint8_t>(EventType::Error));
        events.push_back(Event{evs[i].data.fd, type, evs[i].data.ptr});
    }
    return n;
#elif defined(__APPLE__)
    struct kevent evs[1024];
    struct timespec ts;
    struct timespec* tsp = nullptr;
    if (timeout_ms >= 0) {
        ts.tv_sec = timeout_ms / 1000;
        ts.tv_nsec = (timeout_ms % 1000) * 1000000;
        tsp = &ts;
    }
    int n = ::kevent(kqueue_fd_, nullptr, 0, evs, 1024, tsp);
    if (n < 0) {
        if (errno == EINTR) return 0;
        return std::unexpected(std::error_code(errno, std::generic_category()));
    }
    events.reserve(n);
    for (int i = 0; i < n; ++i) {
        EventType type{};
        if (evs[i].filter == EVFILT_READ) type = EventType::Readable;
        if (evs[i].filter == EVFILT_WRITE) type = EventType::Writable;
        if (evs[i].flags & EV_ERROR) type = EventType::Error;
        events.push_back(Event{static_cast<int>(evs[i].ident), type, evs[i].udata});
    }
    return n;
#endif
}

}  // namespace net
