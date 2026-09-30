#include "network/tcp/tcp_server.hpp"

#include <cstring>
#include <iostream>

namespace net {

TcpServer::TcpServer(const ServerConfig& config) : config_(config) {}

TcpServer::~TcpServer() noexcept {
    stop();
}

std::expected<void, std::error_code> TcpServer::start() noexcept {
    if (running_.load(std::memory_order_relaxed))
        return std::unexpected(std::error_code(EINVAL, std::generic_category()));

    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0)
        return std::unexpected(std::error_code(errno, std::generic_category()));

    listen_fd_ = Socket(fd);

    if (auto r = listen_fd_.set_reuseaddr(config_.reuseaddr); !r)
        return std::unexpected(r.error());
    if (config_.reuseport) {
        if (auto r = listen_fd_.set_reuseport(true); !r)
            return std::unexpected(r.error());
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(config_.port);
    ::inet_pton(AF_INET, config_.host.c_str(), &addr.sin_addr);

    if (auto r = listen_fd_.bind(addr); !r)
        return std::unexpected(r.error());
    if (auto r = listen_fd_.listen(config_.backlog); !r)
        return std::unexpected(r.error());
    if (auto r = listen_fd_.set_nonblocking(); !r)
        return std::unexpected(r.error());

    loop_ = std::make_unique<EventLoop>();
    if (auto r = loop_->add_fd(listen_fd_.fd(), EventType::Readable, nullptr); !r)
        return std::unexpected(r.error());

    running_.store(true, std::memory_order_release);
    thread_ = std::thread([this] {
        std::vector<Event> events;
        while (running_.load(std::memory_order_relaxed)) {
            auto n = loop_->poll(events, config_.timeout_ms);
            if (!n || *n < 0) continue;
            for (const auto& ev : events) {
                if (ev.fd == listen_fd_.fd()) {
                    accept_connections();
                } else {
                    handle_client(ev.fd, ev.type);
                }
            }
        }
    });

    return {};
}

void TcpServer::stop() noexcept {
    if (!running_.exchange(false, std::memory_order_acq_rel)) return;
    if (thread_.joinable()) thread_.join();
    loop_.reset();
    listen_fd_.close();
    client_buffers_.clear();
}

void TcpServer::accept_connections() noexcept {
    while (true) {
        sockaddr_in client_addr{};
        auto client = listen_fd_.accept(&client_addr);
        if (!client) {
            if (client.error() == make_error_code(SocketError::WouldBlock))
                break;
            continue;
        }

        if (auto r = client->set_nonblocking(); !r) {
            client->close();
            continue;
        }
        if (config_.tcp_nodelay) {
            if (auto r = client->set_tcp_nodelay(true); !r) {
                client->close();
                continue;
            }
        }
        if (config_.tcp_quickack) {
            client->set_tcp_quickack(true);
        }

        int cfd = client->fd();
        if (auto r = loop_->add_fd(cfd, EventType::Readable, nullptr); !r) {
            client->close();
            continue;
        }

        client_buffers_[cfd] = Buffer(4096);
        if (on_connect_) on_connect_(cfd);
    }
}

void TcpServer::handle_client(int client_fd, EventType type) noexcept {
    if (type & EventType::Error) {
        close_client(client_fd);
        return;
    }

    if (type & EventType::Readable) {
        char buf[4096];
        Socket client_sock(client_fd);
        while (true) {
            auto n = client_sock.recv(buf, sizeof(buf));
            if (!n) {
                if (n.error() == make_error_code(SocketError::WouldBlock))
                    return;
                close_client(client_fd);
                return;
            }
            auto& buffer = client_buffers_[client_fd];
            buffer.append(buf, *n);
            if (on_message_) on_message_(client_fd, buffer);
        }
    }
}

void TcpServer::close_client(int client_fd) noexcept {
    loop_->remove_fd(client_fd);
    client_buffers_.erase(client_fd);
    ::close(client_fd);
    if (on_disconnect_) on_disconnect_(client_fd);
}

std::expected<void, std::error_code> TcpServer::send(int client_fd, const void* data, size_t len) noexcept {
    Socket s(client_fd);
    auto n = s.send(data, len);
    if (!n) return std::unexpected(n.error());
    return {};
}

std::expected<void, std::error_code> TcpServer::broadcast(const void* data, size_t len) noexcept {
    for (auto& [fd, _] : client_buffers_) {
        auto r = send(fd, data, len);
        if (!r) return std::unexpected(r.error());
    }
    return {};
}

}  // namespace net
