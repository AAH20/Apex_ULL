#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>
#include <memory>

namespace net {

class ZeroCopyBuffer {
public:
    ZeroCopyBuffer() noexcept = default;
    explicit ZeroCopyBuffer(size_t capacity);

    [[nodiscard]] std::span<std::byte> data() noexcept {
        return std::span<std::byte>(ptr_.get(), capacity_);
    }
    [[nodiscard]] std::span<const std::byte> data() const noexcept {
        return std::span<const std::byte>(ptr_.get(), capacity_);
    }
    [[nodiscard]] size_t capacity() const noexcept { return capacity_; }
    [[nodiscard]] size_t size() const noexcept { return size_; }
    void set_size(size_t n) noexcept { size_ = n; }

    void reset() noexcept { size_ = 0; }

private:
    struct Deleter {
        void operator()(std::byte* p) const noexcept;
    };
    std::unique_ptr<std::byte[], Deleter> ptr_;
    size_t capacity_ = 0;
    size_t size_ = 0;
};

class BufferPool {
public:
    explicit BufferPool(size_t buffer_size, size_t count);
    ~BufferPool() noexcept;

    BufferPool(const BufferPool&) = delete;
    BufferPool& operator=(const BufferPool&) = delete;

    [[nodiscard]] ZeroCopyBuffer* acquire() noexcept;
    void release(ZeroCopyBuffer* buf) noexcept;

    [[nodiscard]] size_t buffer_size() const noexcept { return buffer_size_; }
    [[nodiscard]] size_t pool_size() const noexcept { return pool_.size(); }
    [[nodiscard]] size_t available() const noexcept { return available_.size(); }

private:
    size_t buffer_size_;
    std::vector<ZeroCopyBuffer> pool_;
    std::vector<ZeroCopyBuffer*> available_;
};

}  // namespace net
