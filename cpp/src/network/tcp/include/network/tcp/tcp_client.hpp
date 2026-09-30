#pragma once

#include "network/tcp/socket.hpp"
#include "network/tcp/event_loop.hpp"
#include "network/tcp/buffer.hpp"

#include <atomic>
#include <functional>
#include <memory>
#include <string>
#include <thread>

namespace net {

struct ClientConfig {
    std::string host = "127.0.0.1";
    uint16_t port = 8080;
    int timeout_ms = 5000;
    bool tcp_nodelay = true;
    bool tcp_quickack = true;
};

class TcpClient {
public:
    using MessageHandler = std::function<void(Buffer& data)>;
    using DisconnectHandler = std::function<void()>;

    explicit TcpClient(const ClientConfig& config);
    ~TcpClient() noexcept;

    TcpClient(const TcpClient&) = delete;
    TcpClient& operator=(const TcpClient&) = delete;

    std::expected<void, std::error_code> connect() noexcept;
    void disconnect() noexcept;
    [[nodiscard]] bool connected() const noexcept { return connected_.load(std::memory_order_relaxed); }

    std::expected<size_t, std::error_code> send(const void* data, size_t len) noexcept;
    std::expected<size_t, std::error_code> send(std::span<const std::byte> data) noexcept;

    void on_message(MessageHandler h) { on_message_ = std::move(h); }
    void on_disconnect(DisconnectHandler h) { on_disconnect_ = std::move(h); }

    [[nodiscard]] int fd() const noexcept { return socket_.fd(); }

private:
    void receive_loop() noexcept;

    ClientConfig config_;
    Socket socket_;
    std::atomic<bool> connected_{false};
    std::thread thread_;
    Buffer recv_buffer_;

    MessageHandler on_message_;
    DisconnectHandler on_disconnect_;
};

}  // namespace net
