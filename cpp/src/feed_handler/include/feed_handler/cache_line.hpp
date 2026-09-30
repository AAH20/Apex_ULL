#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <new>
#include <utility>
#if defined(__x86_64__) || defined(__i386__)
#include <immintrin.h>
#endif

namespace feed_handler {

/// Cache-line size for x86_64 / ARM64 (64 bytes is the common denominator).
inline constexpr std::size_t kCacheLineSize = 64;

/// Align a value up to the next multiple of kCacheLineSize.
[[nodiscard]] constexpr std::size_t align_up(std::size_t value, std::size_t alignment = kCacheLineSize) noexcept {
    return (value + alignment - 1) & ~(alignment - 1);
}

/// Round up to the next power of two.
[[nodiscard]] constexpr std::size_t next_power_of_two(std::size_t n) noexcept {
    if (n == 0) return 1;
    --n;
    n |= n >> 1;
    n |= n >> 2;
    n |= n >> 4;
    n |= n >> 8;
    n |= n >> 16;
    n |= n >> 32;
    return n + 1;
}

/// Prefetch a cache line for read.
#if defined(__x86_64__) || defined(__i386__)
inline void prefetch_read(const void* ptr) noexcept { _mm_prefetch(static_cast<const char*>(ptr), _MM_HINT_T0); }
#elif defined(__aarch64__)
inline void prefetch_read(const void* ptr) noexcept { __builtin_prefetch(ptr, 0, 3); }
#else
inline void prefetch_read(const void*) noexcept {}
#endif

/// Compiler barrier — prevents reordering across this point.
inline void compiler_barrier() noexcept { asm volatile("" ::: "memory"); }

/// Full memory barrier.
inline void memory_barrier() noexcept { std::atomic_thread_fence(std::memory_order_seq_cst); }

/// Acquire fence — pairs with release store.
inline void acquire_fence() noexcept { std::atomic_thread_fence(std::memory_order_acquire); }

/// Release fence — pairs with acquire load.
inline void release_fence() noexcept { std::atomic_thread_fence(std::memory_order_release); }

/// Cache-line-aligned storage that avoids false sharing.
template <typename T>
struct alignas(kCacheLineSize) CacheAligned {
    T value;

    CacheAligned() = default;
    template <typename U>
    explicit CacheAligned(U&& v) : value(std::forward<U>(v)) {}

    CacheAligned(const CacheAligned&) = default;
    CacheAligned& operator=(const CacheAligned&) = default;
    CacheAligned(CacheAligned&&) = default;
    CacheAligned& operator=(CacheAligned&&) = default;
};

/// A cache-line-padded value that sits alone on a cache line.
template <typename T>
struct Padded {
    alignas(kCacheLineSize) T value;
    char padding[kCacheLineSize - sizeof(T)];

    Padded() = default;
    explicit Padded(T v) : value(v) {}
};

}  // namespace feed_handler
