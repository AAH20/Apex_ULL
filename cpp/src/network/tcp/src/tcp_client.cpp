#include "network/tcp/tcp_client.hpp"

#include <cstring>

namespace net {

TcpClient::TcpClient(const ClientConfig& config)
    : config_(config), recv_buffer_(4096) {}

TcpClient::~TcpClient() noexcept {
    disconnect();
}

std::expected<void, std::error_code> TcpClient::connect() noexcept {
    if (connected_.load(std::memory_order_relaxed))
        return std::unexpected(std::error_code(EINVAL, std::generic_category()));

    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0)
        return std::unexpected(std::error_code(errno, std::generic_category()));

    socket_ = Socket(fd);

    if (auto r = socket_.set_nonblocking(); !r)
        return std::unexpected(r.error());
    if (config_.tcp_nodelay) {
        if (auto r = socket_.set_tcp_nodelay(true); !r)
            return std::unexpected(r.error());
    }
    if (config_.tcp_quickack) {
        socket_.set_tcp_quickack(true);
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(config_.port);
    ::inet_pton(AF_INET, config_.host.c_str(), &addr.sin_addr);

    if (auto r = socket_.connect(addr); !r)
        return std::unexpected(r.error());

    connected_.store(true, std::memory_order_release);
    thread_ = std::thread([this] { receive_loop(); });
    return {};
}

void TcpClient::disconnect() noexcept {
    if (!connected_.exchange(false, std::memory_order_acq_rel)) return;
    socket_.close();
    if (thread_.joinable()) thread_.join();
    if (on_disconnect_) on_disconnect_();
}

std::expected<size_t, std::error_code> TcpClient::send(const void* data, size_t len) noexcept {
    return socket_.send(data, len);
}

std::expected<size_t, std::error_code> TcpClient::send(std::span<const std::byte> data) noexcept {
    return socket_.send(data.data(), data.size());
}

void TcpClient::receive_loop() noexcept {
    char buf[4096];
    while (connected_.load(std::memory_order_relaxed)) {
        auto n = socket_.recv(buf, sizeof(buf));
        if (!n) {
            if (n.error() == make_error_code(SocketError::WouldBlock)) {
                std::this_thread::sleep_for(std::chrono::microseconds(10));
                continue;
            }
            connected_.store(false, std::memory_order_release);
            if (on_disconnect_) on_disconnect_();
            return;
        }
        recv_buffer_.append(buf, *n);
        if (on_message_) on_message_(recv_buffer_);
    }
}

}  // namespace net
