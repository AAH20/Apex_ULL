#pragma once

#include "cache_line.hpp"

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <new>
#include <optional>
#include <type_traits>
#include <limits>
#include <stdexcept>

namespace feed_handler {

/// Lock-free single-producer single-consumer ring buffer.
///
/// Design:
///  - Power-of-2 capacity for fast modulo via bitmask.
///  - Head and tail on separate cache lines to prevent false sharing.
///  - Acquire/release memory ordering for correct synchronization.
///  - No dynamic allocation after construction.
///
/// Thread safety: exactly one producer thread and one consumer thread.
template <typename T>
class SpscRing {
public:
    static_assert(std::is_nothrow_move_constructible_v<T>, "ring elements require nothrow move construction");
    static_assert(std::is_nothrow_destructible_v<T>, "ring elements require nothrow destruction");

    /// Construct a ring with capacity rounded up to the next power of two.
    explicit SpscRing(std::size_t capacity)
        : capacity_(checked_capacity(capacity)),
          mask_(capacity_ - 1),
          buffer_(static_cast<T*>(::operator new[](capacity_ * sizeof(T),
                                                      std::align_val_t{alignof(T)}))) {
        if (!buffer_) {
            throw std::bad_alloc();
        }
    }

    ~SpscRing() {
        // Destroy any remaining elements.
        auto tail = tail_.value.load(std::memory_order_relaxed);
        const auto head = head_.value.load(std::memory_order_relaxed);
        while (tail != head) std::destroy_at(&buffer_[tail++ & mask_]);
        ::operator delete[](buffer_, std::align_val_t{alignof(T)});
    }

    SpscRing(const SpscRing&) = delete;
    SpscRing& operator=(const SpscRing&) = delete;
    SpscRing(SpscRing&&) = delete;
    SpscRing& operator=(SpscRing&&) = delete;

    /// Number of elements the ring can hold.
    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

    /// Current number of elements in the ring.
    [[nodiscard]] std::size_t size() const noexcept {
        const auto head = head_.value.load(std::memory_order_relaxed);
        const auto tail = tail_.value.load(std::memory_order_relaxed);
        return head - tail;
    }

    [[nodiscard]] bool empty() const noexcept { return size() == 0; }

    [[nodiscard]] bool full() const noexcept { return size() == capacity_; }

    /// Push an element. Returns false if the ring is full.
    /// Must be called from the producer thread only.
    bool push(T&& item) noexcept {
        const auto head = head_.value.load(std::memory_order_relaxed);
        const auto next_head = head + 1;

        if (next_head - tail_.value.load(std::memory_order_acquire) > capacity_) {
            return false;  // full
        }

        std::construct_at(&buffer_[head & mask_], std::move(item));
        head_.value.store(next_head, std::memory_order_release);
        return true;
    }

    /// Push a copy. Returns false if the ring is full.
    bool push(const T& item) noexcept(std::is_nothrow_copy_constructible_v<T>) {
        const auto head = head_.value.load(std::memory_order_relaxed);
        const auto next_head = head + 1;

        if (next_head - tail_.value.load(std::memory_order_acquire) > capacity_) {
            return false;
        }

        std::construct_at(&buffer_[head & mask_], item);
        head_.value.store(next_head, std::memory_order_release);
        return true;
    }

    /// Pop an element. Returns std::nullopt if the ring is empty.
    /// Must be called from the consumer thread only.
    std::optional<T> pop() noexcept {
        const auto tail = tail_.value.load(std::memory_order_relaxed);

        if (head_.value.load(std::memory_order_acquire) == tail) {
            return std::nullopt;  // empty
        }

        std::optional<T> item(std::in_place, std::move(buffer_[tail & mask_]));
        std::destroy_at(&buffer_[tail & mask_]);
        tail_.value.store(tail + 1, std::memory_order_release);
        return item;
    }

    /// Peek at the next element without removing it.
    /// Returns nullptr if the ring is empty.
    const T* peek() const noexcept {
        const auto tail = tail_.value.load(std::memory_order_relaxed);
        if (head_.value.load(std::memory_order_acquire) == tail) {
            return nullptr;
        }
        return &buffer_[tail & mask_];
    }

private:
    static std::size_t checked_capacity(std::size_t capacity) {
        const auto max = std::numeric_limits<std::size_t>::max();
        if (capacity == 0 || capacity > (max >> 1) || capacity > max / sizeof(T))
            throw std::invalid_argument("invalid ring capacity");
        const auto rounded = next_power_of_two(capacity);
        if (rounded > max / sizeof(T)) throw std::length_error("ring allocation overflow");
        return rounded;
    }

    // Separate cache lines for head and tail to prevent false sharing.
    alignas(kCacheLineSize) CacheAligned<std::atomic<std::size_t>> head_{std::size_t{0}};
    alignas(kCacheLineSize) CacheAligned<std::atomic<std::size_t>> tail_{std::size_t{0}};

    const std::size_t capacity_;
    const std::size_t mask_;
    T* const buffer_;
};

}  // namespace feed_handler
