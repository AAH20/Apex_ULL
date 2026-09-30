#include "network/udp/udp_socket.hpp"

#include <cstring>

namespace net {

std::error_code make_error_code(UdpSocketError e) noexcept {
    return std::error_code(static_cast<int>(e), std::generic_category());
}

UdpSocket::~UdpSocket() noexcept {
    close();
}

UdpSocket::UdpSocket(UdpSocket&& other) noexcept
    : fd_(other.fd_), connected_(other.connected_) {
    other.fd_ = -1;
    other.connected_ = false;
}

UdpSocket& UdpSocket::operator=(UdpSocket&& other) noexcept {
    if (this != &other) {
        close();
        fd_ = other.fd_;
        connected_ = other.connected_;
        other.fd_ = -1;
        other.connected_ = false;
    }
    return *this;
}

void UdpSocket::close() noexcept {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
    connected_ = false;
}

compat::expected<void, std::error_code> UdpSocket::create() noexcept {
    if (fd_ >= 0) return {};
    fd_ = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_ < 0)
        return compat::unexpected(make_error_code(UdpSocketError::InvalidSocket));
    return {};
}

compat::expected<void, std::error_code> UdpSocket::set_nonblocking() noexcept {
    int flags = ::fcntl(fd_, F_GETFL, 0);
    if (flags < 0)
        return compat::unexpected(make_error_code(UdpSocketError::SetOptionFailed));
    if (::fcntl(fd_, F_SETFL, flags | O_NONBLOCK) < 0)
        return compat::unexpected(make_error_code(UdpSocketError::SetOptionFailed));
    return {};
}

compat::expected<void, std::error_code> UdpSocket::set_reuseaddr(bool enable) noexcept {
    int val = enable ? 1 : 0;
    if (::setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val)) < 0)
        return compat::unexpected(make_error_code(UdpSocketError::SetOptionFailed));
    return {};
}

compat::expected<void, std::error_code> UdpSocket::set_reuseport(bool enable) noexcept {
#if defined(__linux__)
    int val = enable ? 1 : 0;
    if (::setsockopt(fd_, SOL_SOCKET, SO_REUSEPORT, &val, sizeof(val)) < 0)
        return compat::unexpected(make_error_code(UdpSocketError::SetOptionFailed));
#elif defined(__APPLE__)
    (void)enable;
#endif
    return {};
}

compat::expected<void, std::error_code> UdpSocket::set_send_buffer_size(int size) noexcept {
    if (::setsockopt(fd_, SOL_SOCKET, SO_SNDBUF, &size, sizeof(size)) < 0)
        return compat::unexpected(make_error_code(UdpSocketError::SetOptionFailed));
    return {};
}

compat::expected<void, std::error_code> UdpSocket::bind(const sockaddr_in& addr) noexcept {
    if (::bind(fd_, reinterpret_cast<const sockaddr*>(&addr), sizeof(addr)) < 0)
        return compat::unexpected(make_error_code(UdpSocketError::BindFailed));
    return {};
}

compat::expected<void, std::error_code> UdpSocket::connect(const sockaddr_in& addr) noexcept {
    if (connected_) return {};
    if (::connect(fd_, reinterpret_cast<const sockaddr*>(&addr), sizeof(addr)) < 0)
        return compat::unexpected(make_error_code(UdpSocketError::ConnectFailed));
    connected_ = true;
    return {};
}

compat::expected<size_t, std::error_code> UdpSocket::send(const void* data, size_t len) noexcept {
    if (!connected_)
        return compat::unexpected(make_error_code(UdpSocketError::NotConnected));
    ssize_t n = ::send(fd_, data, len, MSG_NOSIGNAL);
    if (n < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
            return compat::unexpected(make_error_code(UdpSocketError::WouldBlock));
        return compat::unexpected(make_error_code(UdpSocketError::SendFailed));
    }
    return static_cast<size_t>(n);
}

compat::expected<size_t, std::error_code> UdpSocket::send_to(const void* data, size_t len,
                                                           const sockaddr_in& dst) noexcept {
    ssize_t n = ::sendto(fd_, data, len, MSG_NOSIGNAL,
                         reinterpret_cast<const sockaddr*>(&dst), sizeof(dst));
    if (n < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
            return compat::unexpected(make_error_code(UdpSocketError::WouldBlock));
        return compat::unexpected(make_error_code(UdpSocketError::SendFailed));
    }
    return static_cast<size_t>(n);
}

}  // namespace net
