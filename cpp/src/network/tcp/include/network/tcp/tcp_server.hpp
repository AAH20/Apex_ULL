#pragma once

#include "network/tcp/socket.hpp"
#include "network/tcp/event_loop.hpp"
#include "network/tcp/buffer.hpp"

#include <atomic>
#include <functional>
#include <memory>
#include <string>
#include <thread>
#include <unordered_map>

namespace net {

struct ServerConfig {
    std::string host = "0.0.0.0";
    uint16_t port = 8080;
    int backlog = 128;
    int max_events = 1024;
    int timeout_ms = -1;
    bool tcp_nodelay = true;
    bool tcp_quickack = true;
    bool reuseaddr = true;
    bool reuseport = false;
};

class TcpServer {
public:
    using MessageHandler = std::function<void(int client_fd, Buffer& data)>;
    using ConnectHandler = std::function<void(int client_fd)>;
    using DisconnectHandler = std::function<void(int client_fd)>;

    explicit TcpServer(const ServerConfig& config);
    ~TcpServer() noexcept;

    TcpServer(const TcpServer&) = delete;
    TcpServer& operator=(const TcpServer&) = delete;

    std::expected<void, std::error_code> start() noexcept;
    void stop() noexcept;
    [[nodiscard]] bool running() const noexcept { return running_.load(std::memory_order_relaxed); }

    void on_message(MessageHandler h) { on_message_ = std::move(h); }
    void on_connect(ConnectHandler h) { on_connect_ = std::move(h); }
    void on_disconnect(DisconnectHandler h) { on_disconnect_ = std::move(h); }

    std::expected<void, std::error_code> send(int client_fd, const void* data, size_t len) noexcept;
    std::expected<void, std::error_code> broadcast(const void* data, size_t len) noexcept;

private:
    void accept_connections() noexcept;
    void handle_client(int client_fd, EventType type) noexcept;
    void close_client(int client_fd) noexcept;

    ServerConfig config_;
    Socket listen_fd_;
    std::unique_ptr<EventLoop> loop_;
    std::atomic<bool> running_{false};
    std::thread thread_;

    std::unordered_map<int, Buffer> client_buffers_;

    MessageHandler on_message_;
    ConnectHandler on_connect_;
    DisconnectHandler on_disconnect_;
};

}  // namespace net
