#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>
#include <span>

namespace net {

class Buffer {
public:
    Buffer() = default;
    explicit Buffer(size_t capacity) { data_.reserve(capacity); }

    void append(const void* data, size_t len) noexcept;
    void append(std::span<const std::byte> data) noexcept;

    [[nodiscard]] std::span<const std::byte> data() const noexcept { return data_; }
    [[nodiscard]] std::span<std::byte> writable() noexcept;
    [[nodiscard]] size_t size() const noexcept { return size_; }
    [[nodiscard]] size_t capacity() const noexcept { return data_.capacity(); }
    [[nodiscard]] bool empty() const noexcept { return size_ == 0; }

    void consume(size_t len) noexcept;
    void clear() noexcept;

    void reserve(size_t cap) { data_.reserve(cap); }

private:
    std::vector<std::byte> data_;
    size_t size_ = 0;
};

}  // namespace net
