#include "network/udp/udp_sender.hpp"

#include <cstring>

namespace net {

UdpSender::UdpSender(const UdpSenderConfig& config)
    : config_(config), pool_(config.buffer_size, config.buffer_pool_size) {}

UdpSender::~UdpSender() noexcept = default;

std::expected<void, std::error_code> UdpSender::initialize() noexcept {
    auto r = socket_.create();
    if (!r) return r;

    r = socket_.set_reuseaddr(true);
    if (!r) return r;

    r = socket_.set_nonblocking();
    if (!r) return r;

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(0);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    r = socket_.bind(addr);
    if (!r) return r;

    return {};
}

std::expected<void, std::error_code> UdpSender::connect(const sockaddr_in& addr) noexcept {
    peer_ = addr;
    has_peer_ = true;
    if (config_.use_connected)
        return socket_.connect(addr);
    return {};
}

std::expected<size_t, std::error_code> UdpSender::send(const void* data, size_t len) noexcept {
    if (config_.use_connected)
        return socket_.send(data, len);
    if (!has_peer_)
        return std::unexpected(make_error_code(UdpSocketError::NotConnected));
    return socket_.send_to(data, len, peer_);
}

std::expected<size_t, std::error_code> UdpSender::send(std::span<const std::byte> data) noexcept {
    return send(data.data(), data.size());
}

std::expected<size_t, std::error_code> UdpSender::send_to(const void* data, size_t len,
                                                          const sockaddr_in& dst) noexcept {
    return socket_.send_to(data, len, dst);
}

}  // namespace net
