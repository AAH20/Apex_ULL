#pragma once

#include <cstdint>
#include <string>
#include <system_error>
#include <expected>

#if defined(__linux__)
    #include <sys/epoll.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netinet/tcp.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <fcntl.h>
#elif defined(__APPLE__)
    #include <sys/types.h>
    #include <sys/event.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netinet/tcp.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <fcntl.h>
#endif

namespace net {

enum class SocketError {
    WouldBlock,
    ConnectionRefused,
    ConnectionReset,
    Timeout,
    InvalidSocket,
    BindFailed,
    ListenFailed,
    AcceptFailed,
    ConnectFailed,
    SendFailed,
    RecvFailed,
    SetOptionFailed,
    GetOptionFailed,
    Unknown
};

std::error_code make_error_code(SocketError e) noexcept;

class Socket {
public:
    Socket() noexcept = default;
    explicit Socket(int fd) noexcept : fd_(fd) {}
    ~Socket() noexcept;

    Socket(const Socket&) = delete;
    Socket& operator=(const Socket&) = delete;
    Socket(Socket&& other) noexcept;
    Socket& operator=(Socket&& other) noexcept;

    [[nodiscard]] int fd() const noexcept { return fd_; }
    [[nodiscard]] bool valid() const noexcept { return fd_ >= 0; }

    std::expected<void, std::error_code> set_nonblocking() noexcept;
    std::expected<void, std::error_code> set_tcp_nodelay(bool enable) noexcept;
    std::expected<void, std::error_code> set_tcp_quickack(bool enable) noexcept;
    std::expected<void, std::error_code> set_reuseaddr(bool enable) noexcept;
    std::expected<void, std::error_code> set_reuseport(bool enable) noexcept;

    std::expected<void, std::error_code> bind(const sockaddr_in& addr) noexcept;
    std::expected<void, std::error_code> listen(int backlog = 128) noexcept;
    std::expected<Socket, std::error_code> accept(sockaddr_in* client_addr = nullptr) noexcept;
    std::expected<void, std::error_code> connect(const sockaddr_in& addr) noexcept;

    std::expected<size_t, std::error_code> send(const void* data, size_t len) noexcept;
    std::expected<size_t, std::error_code> recv(void* buf, size_t len) noexcept;

    void close() noexcept;

private:
    int fd_ = -1;
};

}  // namespace net
