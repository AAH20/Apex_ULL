#pragma once

#include "dpdk_bypass.hpp"
#include "market_data.hpp"
#include "parser.hpp"
#include "spsc_ring.hpp"

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <span>
#include <thread>
#include <vector>

namespace feed_handler {

/// Configuration for the feed handler.
struct FeedHandlerConfig {
    std::size_t ring_size = 65536;           // Must be power of 2.
    std::size_t rx_burst_size = 32;          // Max packets per RX burst.
    std::size_t parser_queue_size = 16384;   // Parsed message queue.
    bool use_dpdk_stub = true;               // Use stub for dev/test.
    std::string dpdk_port_name = "eth0";
    std::size_t dpdk_rx_desc = 4096;
    std::size_t dpdk_tx_desc = 4096;
};

/// Statistics for the feed handler.
struct FeedHandlerStats {
    uint64_t packets_received = 0;
    uint64_t packets_dropped = 0;
    uint64_t messages_parsed = 0;
    uint64_t messages_forwarded = 0;
    uint64_t parse_errors = 0;
    uint64_t ring_full_events = 0;
    uint64_t total_latency_nanos = 0;  // Sum for averaging.
    uint64_t min_latency_nanos = UINT64_MAX;
    uint64_t max_latency_nanos = 0;
};

/// High-performance market-data feed handler.
///
/// Pipeline:
///   NIC RX (DPDK) → SPSC ring → Parser → SPSC ring → Strategy callback
///
/// All hot-path data structures are cache-line aligned.
/// Zero-copy parsing: messages are parsed directly from packet buffers.
class FeedHandler {
public:
    using MessageCallback = std::function<void(const MarketDataMessage&, uint64_t /*rx_timestamp*/)>;

    explicit FeedHandler(const FeedHandlerConfig& config);
    ~FeedHandler();

    FeedHandler(const FeedHandler&) = delete;
    FeedHandler& operator=(const FeedHandler&) = delete;

    /// Initialize the feed handler (DPDK port, rings, etc.).
    bool initialize();

    /// Start processing in a background thread.
    bool start();

    /// Stop processing.
    void stop();

    /// Set the callback for parsed messages.
    void set_callback(MessageCallback cb);

    /// Get current statistics.
    FeedHandlerStats get_stats() const;

    /// Check if running.
    [[nodiscard]] bool is_running() const;

    /// Process a single packet (for testing / manual injection).
    /// Returns the number of messages parsed.
    std::size_t process_packet(std::span<const uint8_t> packet_data, uint64_t rx_timestamp);

private:
    void processing_loop();
    void process_rx_burst();
    void forward_messages();

    FeedHandlerConfig config_;
    std::unique_ptr<DpdkPort> port_;

    // SPSC rings for the pipeline.
    std::unique_ptr<SpscRing<DpdkPort::Packet>> rx_ring_;
    std::unique_ptr<SpscRing<MarketDataMessage>> msg_ring_;

    // Callback for parsed messages.
    MessageCallback callback_;

    // Processing thread.
    std::thread processing_thread_;
    std::atomic<bool> running_{false};

    // Statistics (cache-line aligned to avoid false sharing with callback).
    alignas(64) mutable std::atomic<uint64_t> packets_received_{0};
    alignas(64) mutable std::atomic<uint64_t> packets_dropped_{0};
    alignas(64) mutable std::atomic<uint64_t> messages_parsed_{0};
    alignas(64) mutable std::atomic<uint64_t> messages_forwarded_{0};
    alignas(64) mutable std::atomic<uint64_t> parse_errors_{0};
    alignas(64) mutable std::atomic<uint64_t> ring_full_events_{0};
    alignas(64) mutable std::atomic<uint64_t> total_latency_nanos_{0};
    alignas(64) mutable std::atomic<uint64_t> min_latency_nanos_{UINT64_MAX};
    alignas(64) mutable std::atomic<uint64_t> max_latency_nanos_{0};
};

}  // namespace feed_handler
