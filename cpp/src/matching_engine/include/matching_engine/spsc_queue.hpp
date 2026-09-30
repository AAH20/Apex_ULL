#pragma once

#include "matching_engine/types.hpp"

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <new>
#include <optional>

namespace matching_engine {

inline constexpr std::size_t kCacheLineSize = 64;

[[nodiscard]] constexpr std::size_t next_power_of_two(std::size_t n) noexcept {
    if (n == 0) return 1;
    --n;
    n |= n >> 1; n |= n >> 2; n |= n >> 4;
    n |= n >> 8; n |= n >> 16; n |= n >> 32;
    return n + 1;
}

template <typename T>
struct alignas(kCacheLineSize) CacheAligned {
    T value;
    CacheAligned() = default;
    template <typename U>
    explicit CacheAligned(U&& v) : value(std::forward<U>(v)) {}
};

template <typename T>
class SpscQueue {
public:
    explicit SpscQueue(std::size_t capacity)
        : capacity_(next_power_of_two(capacity)),
          mask_(capacity_ - 1),
          buffer_(static_cast<T*>(::operator new[](capacity_ * sizeof(T),
                                                      std::align_val_t{alignof(T)}))) {
        if (!buffer_) throw std::bad_alloc();
    }

    ~SpscQueue() {
        while (pop()) {}
        ::operator delete[](buffer_, std::align_val_t{alignof(T)});
    }

    SpscQueue(const SpscQueue&) = delete;
    SpscQueue& operator=(const SpscQueue&) = delete;
    SpscQueue(SpscQueue&&) = delete;
    SpscQueue& operator=(SpscQueue&&) = delete;

    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }
    [[nodiscard]] std::size_t size() const noexcept {
        return head_.value.load(std::memory_order_relaxed) -
               tail_.value.load(std::memory_order_relaxed);
    }
    [[nodiscard]] bool empty() const noexcept { return size() == 0; }
    [[nodiscard]] bool full() const noexcept { return size() == capacity_; }

    bool push(T&& item) noexcept {
        const auto head = head_.value.load(std::memory_order_relaxed);
        const auto next_head = head + 1;
        if (next_head - tail_.value.load(std::memory_order_acquire) > capacity_)
            return false;
        buffer_[head & mask_] = std::move(item);
        head_.value.store(next_head, std::memory_order_release);
        return true;
    }

    bool push(const T& item) noexcept {
        const auto head = head_.value.load(std::memory_order_relaxed);
        const auto next_head = head + 1;
        if (next_head - tail_.value.load(std::memory_order_acquire) > capacity_)
            return false;
        buffer_[head & mask_] = item;
        head_.value.store(next_head, std::memory_order_release);
        return true;
    }

    std::optional<T> pop() noexcept {
        const auto tail = tail_.value.load(std::memory_order_relaxed);
        if (head_.value.load(std::memory_order_acquire) == tail)
            return std::nullopt;
        T item = std::move(buffer_[tail & mask_]);
        tail_.value.store(tail + 1, std::memory_order_release);
        return item;
    }

private:
    alignas(kCacheLineSize) CacheAligned<std::atomic<std::size_t>> head_{0};
    alignas(kCacheLineSize) CacheAligned<std::atomic<std::size_t>> tail_{0};
    const std::size_t capacity_;
    const std::size_t mask_;
    T* const buffer_;
};

}  // namespace matching_engine
