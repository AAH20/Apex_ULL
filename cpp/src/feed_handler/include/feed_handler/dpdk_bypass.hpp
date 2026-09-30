#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>
#include <string>

namespace feed_handler {

/// DPDK kernel-bypass interface.
///
/// On Linux with DPDK installed, this wraps rte_eth_* APIs for zero-copy
/// packet I/O. On other platforms (macOS dev, CI), it provides a stub that
/// reads from a memory buffer for testing.
///
/// The abstraction allows the feed handler to be developed and tested
/// without a DPDK-capable NIC, then deployed on production hardware.
class DpdkPort {
public:
    struct Config {
        std::string port_name;
        std::size_t num_rx_desc = 4096;
        std::size_t num_tx_desc = 4096;
        std::size_t mbuf_pool_size = 65536;
    };

    struct Packet {
        std::span<const uint8_t> data;
        uint64_t timestamp_nanos;
        uint32_t port_id;
        uint32_t queue_id;
    };

    struct Stats {
        uint64_t rx_packets = 0;
        uint64_t rx_bytes = 0;
        uint64_t tx_packets = 0;
        uint64_t tx_bytes = 0;
        uint64_t rx_errors = 0;
        uint64_t tx_errors = 0;
        uint64_t rx_dropped = 0;
        uint64_t imissed = 0;
    };

    virtual ~DpdkPort() = default;

    /// Initialize the port. Returns true on success.
    virtual bool init(const Config& config) = 0;

    /// Start packet processing.
    virtual bool start() = 0;

    /// Stop packet processing.
    virtual void stop() = 0;

    /// Receive a batch of packets (up to max_packets).
    /// Returns the number of packets received.
    virtual std::size_t rx_burst(Packet* packets, std::size_t max_packets) = 0;

    /// Send a batch of packets.
    /// Returns the number of packets sent.
    virtual std::size_t tx_burst(const Packet* packets, std::size_t count) = 0;

    /// Get port statistics.
    virtual Stats get_stats() const = 0;

    /// Check if the port is initialized.
    [[nodiscard]] virtual bool is_initialized() const = 0;
};

/// Factory: create a DPDK port or a stub port.
/// Set use_stub=true for development/testing without DPDK hardware.
std::unique_ptr<DpdkPort> create_dpdk_port(bool use_stub = true);

/// Stub implementation for development and testing.
class DpdkStubPort : public DpdkPort {
public:
    bool init(const Config& config) override;
    bool start() override;
    void stop() override;
    std::size_t rx_burst(Packet* packets, std::size_t max_packets) override;
    std::size_t tx_burst(const Packet* packets, std::size_t count) override;
    Stats get_stats() const override;
    [[nodiscard]] bool is_initialized() const override;

    /// Inject a packet for testing (simulates NIC RX).
    void inject_packet(std::span<const uint8_t> data);

private:
    Config config_;
    bool initialized_ = false;
    bool running_ = false;
    Stats stats_;

    // Simple test packet queue.
    static constexpr std::size_t kMaxTestPackets = 1024;
    struct alignas(64) TestPacket {
        std::unique_ptr<uint8_t[]> data;
        std::size_t len;
        uint64_t timestamp;
    };
    TestPacket test_packets_[kMaxTestPackets];
    std::size_t test_head_ = 0;
    std::size_t test_tail_ = 0;
};

}  // namespace feed_handler
