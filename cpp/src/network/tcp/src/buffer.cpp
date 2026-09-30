#include "network/tcp/buffer.hpp"

#include <cstring>

namespace net {

void Buffer::append(const void* data, size_t len) noexcept {
    const auto* bytes = static_cast<const std::byte*>(data);
    data_.insert(data_.end(), bytes, bytes + len);
    size_ += len;
}

void Buffer::append(std::span<const std::byte> data) noexcept {
    data_.insert(data_.end(), data.begin(), data.end());
    size_ += data.size();
}

std::span<std::byte> Buffer::writable() noexcept {
    if (size_ == data_.size()) return {};
    return std::span<std::byte>(data_.data() + size_, data_.size() - size_);
}

void Buffer::consume(size_t len) noexcept {
    if (len >= size_) {
        size_ = 0;
        data_.clear();
        return;
    }
    std::memmove(data_.data(), data_.data() + len, size_ - len);
    size_ -= len;
    data_.resize(size_);
}

void Buffer::clear() noexcept {
    size_ = 0;
    data_.clear();
}

}  // namespace net
