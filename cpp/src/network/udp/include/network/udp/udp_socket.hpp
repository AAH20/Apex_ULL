#pragma once

#include "network/udp/compat/expected.hpp"

#include <cstdint>
#include <span>
#include <system_error>

#if defined(__linux__)
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <fcntl.h>
#elif defined(__APPLE__)
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <fcntl.h>
#endif

namespace net {

enum class UdpSocketError {
    WouldBlock,
    InvalidSocket,
    BindFailed,
    ConnectFailed,
    SendFailed,
    SetOptionFailed,
    NotConnected,
    AlreadyConnected,
    Unknown
};

std::error_code make_error_code(UdpSocketError e) noexcept;

class UdpSocket {
public:
    UdpSocket() noexcept = default;
    explicit UdpSocket(int fd) noexcept : fd_(fd) {}
    ~UdpSocket() noexcept;

    UdpSocket(const UdpSocket&) = delete;
    UdpSocket& operator=(const UdpSocket&) = delete;
    UdpSocket(UdpSocket&& other) noexcept;
    UdpSocket& operator=(UdpSocket&& other) noexcept;

    [[nodiscard]] int fd() const noexcept { return fd_; }
    [[nodiscard]] bool valid() const noexcept { return fd_ >= 0; }
    [[nodiscard]] bool connected() const noexcept { return connected_; }

    std::expected<void, std::error_code> create() noexcept;
    std::expected<void, std::error_code> set_nonblocking() noexcept;
    std::expected<void, std::error_code> set_reuseaddr(bool enable) noexcept;
    std::expected<void, std::error_code> set_reuseport(bool enable) noexcept;
    std::expected<void, std::error_code> set_send_buffer_size(int size) noexcept;

    std::expected<void, std::error_code> bind(const sockaddr_in& addr) noexcept;
    std::expected<void, std::error_code> connect(const sockaddr_in& addr) noexcept;

    std::expected<size_t, std::error_code> send(const void* data, size_t len) noexcept;
    std::expected<size_t, std::error_code> send_to(const void* data, size_t len,
                                                    const sockaddr_in& dst) noexcept;

    void close() noexcept;

private:
    int fd_ = -1;
    bool connected_ = false;
};

}  // namespace net
