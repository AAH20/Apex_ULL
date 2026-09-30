#include "network/tcp/socket.hpp"

#include <cstring>
#include <netdb.h>

namespace net {

std::error_code make_error_code(SocketError e) noexcept {
    return std::error_code(static_cast<int>(e), std::generic_category());
}

Socket::~Socket() noexcept {
    close();
}

Socket::Socket(Socket&& other) noexcept : fd_(other.fd_) {
    other.fd_ = -1;
}

Socket& Socket::operator=(Socket&& other) noexcept {
    if (this != &other) {
        close();
        fd_ = other.fd_;
        other.fd_ = -1;
    }
    return *this;
}

void Socket::close() noexcept {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
}

std::expected<void, std::error_code> Socket::set_nonblocking() noexcept {
    int flags = ::fcntl(fd_, F_GETFL, 0);
    if (flags < 0) return std::unexpected(make_error_code(SocketError::SetOptionFailed));
    if (::fcntl(fd_, F_SETFL, flags | O_NONBLOCK) < 0)
        return std::unexpected(make_error_code(SocketError::SetOptionFailed));
    return {};
}

std::expected<void, std::error_code> Socket::set_tcp_nodelay(bool enable) noexcept {
    int val = enable ? 1 : 0;
    if (::setsockopt(fd_, IPPROTO_TCP, TCP_NODELAY, &val, sizeof(val)) < 0)
        return std::unexpected(make_error_code(SocketError::SetOptionFailed));
    return {};
}

std::expected<void, std::error_code> Socket::set_tcp_quickack(bool enable) noexcept {
#if defined(__linux__)
    int val = enable ? 1 : 0;
    if (::setsockopt(fd_, IPPROTO_TCP, TCP_QUICKACK, &val, sizeof(val)) < 0)
        return std::unexpected(make_error_code(SocketError::SetOptionFailed));
#elif defined(__APPLE__)
    (void)enable;
#endif
    return {};
}

std::expected<void, std::error_code> Socket::set_reuseaddr(bool enable) noexcept {
    int val = enable ? 1 : 0;
    if (::setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val)) < 0)
        return std::unexpected(make_error_code(SocketError::SetOptionFailed));
    return {};
}

std::expected<void, std::error_code> Socket::set_reuseport(bool enable) noexcept {
#if defined(__linux__)
    int val = enable ? 1 : 0;
    if (::setsockopt(fd_, SOL_SOCKET, SO_REUSEPORT, &val, sizeof(val)) < 0)
        return std::unexpected(make_error_code(SocketError::SetOptionFailed));
#elif defined(__APPLE__)
    (void)enable;
#endif
    return {};
}

std::expected<void, std::error_code> Socket::bind(const sockaddr_in& addr) noexcept {
    if (::bind(fd_, reinterpret_cast<const sockaddr*>(&addr), sizeof(addr)) < 0)
        return std::unexpected(make_error_code(SocketError::BindFailed));
    return {};
}

std::expected<void, std::error_code> Socket::listen(int backlog) noexcept {
    if (::listen(fd_, backlog) < 0)
        return std::unexpected(make_error_code(SocketError::ListenFailed));
    return {};
}

std::expected<Socket, std::error_code> Socket::accept(sockaddr_in* client_addr) noexcept {
    sockaddr addr{};
    socklen_t len = sizeof(addr);
    int client_fd = ::accept(fd_, &addr, &len);
    if (client_fd < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
            return std::unexpected(make_error_code(SocketError::WouldBlock));
        return std::unexpected(make_error_code(SocketError::AcceptFailed));
    }
    if (client_addr && len >= sizeof(sockaddr_in))
        std::memcpy(client_addr, &addr, sizeof(sockaddr_in));
    return Socket(client_fd);
}

std::expected<void, std::error_code> Socket::connect(const sockaddr_in& addr) noexcept {
    if (::connect(fd_, reinterpret_cast<const sockaddr*>(&addr), sizeof(addr)) < 0) {
        if (errno == EINPROGRESS) return {};
        if (errno == ECONNREFUSED)
            return std::unexpected(make_error_code(SocketError::ConnectionRefused));
        return std::unexpected(make_error_code(SocketError::ConnectFailed));
    }
    return {};
}

std::expected<size_t, std::error_code> Socket::send(const void* data, size_t len) noexcept {
    ssize_t n = ::send(fd_, data, len, MSG_NOSIGNAL);
    if (n < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
            return std::unexpected(make_error_code(SocketError::WouldBlock));
        return std::unexpected(make_error_code(SocketError::SendFailed));
    }
    return static_cast<size_t>(n);
}

std::expected<size_t, std::error_code> Socket::recv(void* buf, size_t len) noexcept {
    ssize_t n = ::recv(fd_, buf, len, 0);
    if (n < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
            return std::unexpected(make_error_code(SocketError::WouldBlock));
        return std::unexpected(make_error_code(SocketError::RecvFailed));
    }
    if (n == 0)
        return std::unexpected(make_error_code(SocketError::ConnectionReset));
    return static_cast<size_t>(n);
}

}  // namespace net
