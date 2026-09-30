#include "feed_handler/feed_handler.hpp"

#include <algorithm>
#include <chrono>
#include <cstring>
#include <stdexcept>

namespace feed_handler {

FeedHandler::FeedHandler(const FeedHandlerConfig& config)
    : config_(config) {}

FeedHandler::~FeedHandler() {
    stop();
}

bool FeedHandler::initialize() {
    if (config_.rx_burst_size == 0 || config_.rx_burst_size > 256 ||
        config_.ring_size == 0 || config_.parser_queue_size == 0) return false;
    // Create DPDK port.
    port_ = create_dpdk_port(config_.use_dpdk_stub);
    if (!port_) return false;

    DpdkPort::Config port_config;
    port_config.port_name = config_.dpdk_port_name;
    port_config.num_rx_desc = config_.dpdk_rx_desc;
    port_config.num_tx_desc = config_.dpdk_tx_desc;

    if (!port_->init(port_config)) return false;

    // Create SPSC rings.
    rx_ring_ = std::make_unique<SpscRing<DpdkPort::Packet>>(config_.ring_size);
    msg_ring_ = std::make_unique<SpscRing<QueuedMessage>>(config_.parser_queue_size);

    return true;
}

bool FeedHandler::start() {
    if (running_) return false;
    if (!port_ || !port_->is_initialized()) return false;

    if (!port_->start()) return false;

    running_ = true;
    processing_thread_ = std::thread(&FeedHandler::processing_loop, this);
    return true;
}

void FeedHandler::stop() {
    if (!running_) return;
    running_ = false;
    if (processing_thread_.joinable()) {
        processing_thread_.join();
    }
    if (port_) port_->stop();
}

void FeedHandler::set_callback(MessageCallback cb) {
    if (running_) throw std::logic_error("callback changes require a stopped handler");
    callback_ = std::move(cb);
    if (msg_ring_) forward_messages();
}

FeedHandlerStats FeedHandler::get_stats() const {
    FeedHandlerStats stats;
    stats.packets_received = packets_received_.load(std::memory_order_relaxed);
    stats.packets_dropped = packets_dropped_.load(std::memory_order_relaxed);
    stats.messages_parsed = messages_parsed_.load(std::memory_order_relaxed);
    stats.messages_forwarded = messages_forwarded_.load(std::memory_order_relaxed);
    stats.parse_errors = parse_errors_.load(std::memory_order_relaxed);
    stats.ring_full_events = ring_full_events_.load(std::memory_order_relaxed);
    stats.latency_samples = latency_samples_.load(std::memory_order_relaxed);
    stats.total_latency_nanos = total_latency_nanos_.load(std::memory_order_relaxed);
    stats.min_latency_nanos = min_latency_nanos_.load(std::memory_order_relaxed);
    stats.max_latency_nanos = max_latency_nanos_.load(std::memory_order_relaxed);
    return stats;
}

bool FeedHandler::is_running() const {
    return running_;
}

std::size_t FeedHandler::process_packet(std::span<const uint8_t> packet_data,
                                         uint64_t rx_timestamp) {
    Parser parser(packet_data);
    std::size_t count = 0;

    while (parser.has(1)) {
        MarketDataMessage msg;
        if (!parser.parse_message(msg)) {
            ++parse_errors_;
            break;
        }

        ++messages_parsed_;
        ++count;

        // Only comparable steady-clock timestamps qualify; zero means unavailable.
        const auto now = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());
        if (config_.rx_timestamps_are_monotonic && rx_timestamp != 0 && now >= rx_timestamp) {
            const auto latency = now - rx_timestamp;
            latency_samples_.fetch_add(1, std::memory_order_relaxed);
            total_latency_nanos_.fetch_add(latency, std::memory_order_relaxed);
            auto prev_min = min_latency_nanos_.load(std::memory_order_relaxed);
            while (latency < prev_min && !min_latency_nanos_.compare_exchange_weak(prev_min, latency)) {}
            auto prev_max = max_latency_nanos_.load(std::memory_order_relaxed);
            while (latency > prev_max && !max_latency_nanos_.compare_exchange_weak(prev_max, latency)) {}
        }

        // Forward to callback or push to message ring.
        if (callback_) {
            callback_(msg, rx_timestamp);
            ++messages_forwarded_;
        } else {
            if (!msg_ring_->push(QueuedMessage{std::move(msg), rx_timestamp})) {
                ++ring_full_events_;
            }
        }
    }

    return count;
}

void FeedHandler::processing_loop() {
    // Pre-allocate packet array on the stack.
    constexpr std::size_t kMaxBurst = 256;
    std::vector<DpdkPort::Packet> packets(kMaxBurst);

    while (running_) {
        // RX burst from DPDK.
        const auto n = port_->rx_burst(packets.data(), config_.rx_burst_size);
        if (n == 0) {
            // No packets — brief pause to avoid busy-spin.
            std::this_thread::yield();
            continue;
        }

        packets_received_.fetch_add(n, std::memory_order_relaxed);

        // Parse each packet.
        for (std::size_t i = 0; i < n; ++i) {
            process_packet(packets[i].data, packets[i].timestamp_nanos);
        }

        // Forward parsed messages from ring to callback.
        forward_messages();
    }
}

void FeedHandler::forward_messages() {
    if (!callback_) return;

    while (auto queued = msg_ring_->pop()) {
        callback_(queued->message, queued->rx_timestamp);
        ++messages_forwarded_;
    }
}

}  // namespace feed_handler
