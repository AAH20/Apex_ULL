#include "network/udp/zero_copy_buffer.hpp"

#include <cstdlib>
#include <new>

namespace net {

void ZeroCopyBuffer::Deleter::operator()(std::byte* p) const noexcept {
    if (p) ::operator delete[](p, std::align_val_t{64});
}

ZeroCopyBuffer::ZeroCopyBuffer(size_t capacity) : capacity_(capacity) {
    if (capacity > 0) {
        ptr_.reset(static_cast<std::byte*>(
            ::operator new[](capacity, std::align_val_t{64})));
    }
}

BufferPool::BufferPool(size_t buffer_size, size_t count)
    : buffer_size_(buffer_size), pool_(count) {
    for (auto& buf : pool_) {
        buf = ZeroCopyBuffer(buffer_size);
        available_.push_back(&buf);
    }
}

BufferPool::~BufferPool() noexcept = default;

ZeroCopyBuffer* BufferPool::acquire() noexcept {
    if (available_.empty()) return nullptr;
    auto* buf = available_.back();
    available_.pop_back();
    buf->reset();
    return buf;
}

void BufferPool::release(ZeroCopyBuffer* buf) noexcept {
    if (buf) available_.push_back(buf);
}

}  // namespace net
