#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <unordered_map>
#include <vector>
#include <system_error>
#include <expected>

#if defined(__linux__)
    #include <sys/epoll.h>
#elif defined(__APPLE__)
    #include <sys/event.h>
#endif

namespace net {

enum class EventType : uint8_t {
    Readable = 1,
    Writable = 2,
    Error = 4,
    Hangup = 8
};

struct Event {
    int fd;
    EventType type;
    void* user_data;
};

class EventLoop {
public:
    using EventHandler = std::function<void(int fd, EventType, void*)>;

    EventLoop();
    ~EventLoop() noexcept;

    EventLoop(const EventLoop&) = delete;
    EventLoop& operator=(const EventLoop&) = delete;

    std::expected<void, std::error_code> add_fd(int fd, EventType mask, void* user_data) noexcept;
    std::expected<void, std::error_code> modify_fd(int fd, EventType mask, void* user_data) noexcept;
    std::expected<void, std::error_code> remove_fd(int fd) noexcept;

    std::expected<int, std::error_code> poll(std::vector<Event>& events, int timeout_ms = -1) noexcept;

    [[nodiscard]] bool empty() const noexcept { return handlers_.empty(); }

private:
#if defined(__linux__)
    int epoll_fd_ = -1;
#elif defined(__APPLE__)
    int kqueue_fd_ = -1;
#endif
    std::unordered_map<int, std::pair<EventType, void*>> handlers_;
};

}  // namespace net
