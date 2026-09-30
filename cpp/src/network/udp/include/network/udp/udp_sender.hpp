#pragma once

#include "network/udp/compat/expected.hpp"
#include "network/udp/udp_socket.hpp"
#include "network/udp/zero_copy_buffer.hpp"

#include <cstdint>
#include <span>
#include <string>
#include <system_error>

namespace net {

struct UdpSenderConfig {
    std::string host = "127.0.0.1";
    uint16_t port = 9090;
    bool use_connected = true;
    size_t buffer_pool_size = 1024;
    size_t buffer_size = 2048;
};

class UdpSender {
public:
    explicit UdpSender(const UdpSenderConfig& config);
    ~UdpSender() noexcept;

    UdpSender(const UdpSender&) = delete;
    UdpSender& operator=(const UdpSender&) = delete;

    compat::expected<void, std::error_code> initialize() noexcept;
    compat::expected<void, std::error_code> connect(const sockaddr_in& addr) noexcept;

    compat::expected<size_t, std::error_code> send(const void* data, size_t len) noexcept;
    compat::expected<size_t, std::error_code> send(std::span<const std::byte> data) noexcept;
    compat::expected<size_t, std::error_code> send_to(const void* data, size_t len,
                                                    const sockaddr_in& dst) noexcept;

    [[nodiscard]] bool connected() const noexcept { return socket_.connected(); }
    [[nodiscard]] int fd() const noexcept { return socket_.fd(); }

    [[nodiscard]] BufferPool& buffer_pool() noexcept { return pool_; }

private:
    UdpSenderConfig config_;
    UdpSocket socket_;
    BufferPool pool_;
    sockaddr_in peer_{};
    bool has_peer_ = false;
};

}  // namespace net
