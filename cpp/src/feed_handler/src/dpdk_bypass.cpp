#include "feed_handler/dpdk_bypass.hpp"

#include <algorithm>
#include <cstring>

namespace feed_handler {

std::unique_ptr<DpdkPort> create_dpdk_port(bool use_stub) {
    if (use_stub) {
        return std::make_unique<DpdkStubPort>();
    }
    // Real DPDK is not linked by this implementation. Never silently simulate it.
    return nullptr;
}

// ── DpdkStubPort ─────────────────────────────────────────────────────────────

bool DpdkStubPort::init(const Config& config) {
    config_ = config;
    initialized_ = true;
    return true;
}

bool DpdkStubPort::start() {
    if (!initialized_) return false;
    running_ = true;
    return true;
}

void DpdkStubPort::stop() {
    running_ = false;
}

std::size_t DpdkStubPort::rx_burst(Packet* packets, std::size_t max_packets) {
    if (!running_) return 0;

    std::size_t count = 0;
    while (count < max_packets && test_head_ != test_tail_) {
        auto& tp = test_packets_[test_tail_];
        packets[count].data = std::span<const uint8_t>(tp.data.get(), tp.len);
        packets[count].timestamp_nanos = tp.timestamp;
        packets[count].port_id = 0;
        packets[count].queue_id = 0;
        ++count;
        test_tail_ = (test_tail_ + 1) % kMaxTestPackets;
    }

    stats_.rx_packets += count;
    for (std::size_t i = 0; i < count; ++i) {
        stats_.rx_bytes += packets[i].data.size();
    }
    return count;
}

std::size_t DpdkStubPort::tx_burst(const Packet* /*packets*/, std::size_t count) {
    stats_.tx_packets += count;
    return count;
}

DpdkPort::Stats DpdkStubPort::get_stats() const {
    return stats_;
}

bool DpdkStubPort::is_initialized() const {
    return initialized_;
}

void DpdkStubPort::inject_packet(std::span<const uint8_t> data) {
    if (!initialized_) return;

    const auto next_head = (test_head_ + 1) % kMaxTestPackets;
    if (next_head == test_tail_) {
        ++stats_.rx_dropped;
        return;
    }

    auto& tp = test_packets_[test_head_];
    tp.data = std::make_unique<uint8_t[]>(data.size());
    std::memcpy(tp.data.get(), data.data(), data.size());
    tp.len = data.size();
    tp.timestamp = 0;  // Will be set by caller if needed.
    test_head_ = next_head;
}

}  // namespace feed_handler
