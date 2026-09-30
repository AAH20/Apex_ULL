//! Feed handler processor — the main event loop tying DPDK, parsing, and channels together.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use super::channel::{FeedChannel, RawByteChannel, DEFAULT_CHANNEL_CAPACITY};
use super::dpdk::{DpdkConfig, DpdkPort, MockDpdkPort, RealDpdkPort};
use super::protocol::PacketParser;
use super::types::{FeedError, FeedResult, FeedStats};

/// Builder for `FeedHandler`.
pub struct FeedHandlerBuilder {
    dpdk_config: Option<DpdkConfig>,
    channel_capacity: usize,
    use_mock: bool,
    pin_thread: bool,
    thread_name: String,
}

impl Default for FeedHandlerBuilder {
    fn default() -> Self {
        Self {
            dpdk_config: None,
            channel_capacity: DEFAULT_CHANNEL_CAPACITY,
            use_mock: true,
            pin_thread: false,
            thread_name: "feed-handler".to_string(),
        }
    }
}

impl FeedHandlerBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_dpdk_config(mut self, config: DpdkConfig) -> Self {
        self.dpdk_config = Some(config);
        self.use_mock = false;
        self
    }

    pub fn with_channel_capacity(mut self, capacity: usize) -> Self {
        self.channel_capacity = capacity;
        self
    }

    pub fn use_mock(mut self, use_mock: bool) -> Self {
        self.use_mock = use_mock;
        self
    }

    pub fn pin_thread(mut self, pin: bool) -> Self {
        self.pin_thread = pin;
        self
    }

    pub fn thread_name(mut self, name: impl Into<String>) -> Self {
        self.thread_name = name.into();
        self
    }

    pub fn build(self) -> FeedResult<FeedHandler> {
        if self.pin_thread {
            return Err(FeedError::DpdkPortConfig("thread affinity is not implemented; pin externally and disclose it".to_string()));
        }
        let channel = Arc::new(FeedChannel::new(self.channel_capacity));
        let raw_channel = Arc::new(RawByteChannel::new(self.channel_capacity));
        let stats = Arc::new(FeedStats::new());
        let running = Arc::new(AtomicBool::new(false));

        let dpdk_port: Arc<dyn DpdkPort> = if self.use_mock {
            Arc::new(MockDpdkPort::new(0))
        } else {
            let config = self
                .dpdk_config
                .ok_or_else(|| FeedError::DpdkInit("DPDK config required".to_string()))?;
            Arc::new(RealDpdkPort::new(config)?)
        };

        Ok(FeedHandler {
            dpdk_port,
            channel,
            raw_channel,
            stats,
            running,
            pin_thread: self.pin_thread,
            thread_name: self.thread_name,
            thread_handle: None,
        })
    }
}

/// The main feed handler.
///
/// Runs a dedicated thread that:
/// 1. Receives packet bursts from DPDK (kernel bypass)
/// 2. Parses packets into `MarketEvent` (zero-copy)
/// 3. Forwards events to downstream consumers via SPSC channel
pub struct FeedHandler {
    dpdk_port: Arc<dyn DpdkPort>,
    channel: Arc<FeedChannel>,
    raw_channel: Arc<RawByteChannel>,
    stats: Arc<FeedStats>,
    running: Arc<AtomicBool>,
    pin_thread: bool,
    thread_name: String,
    thread_handle: Option<JoinHandle<FeedResult<()>>>,
}

impl FeedHandler {
    /// Start the feed handler thread.
    pub fn start(&mut self) -> FeedResult<()> {
        if self.running.swap(true, Ordering::SeqCst) {
            return Err(FeedError::DpdkInit("already running".to_string()));
        }

        let dpdk_port = Arc::clone(&self.dpdk_port);
        let channel = Arc::clone(&self.channel);
        let raw_channel = Arc::clone(&self.raw_channel);
        let stats = Arc::clone(&self.stats);
        let running = Arc::clone(&self.running);
        let pin_thread = self.pin_thread;
        let thread_name = self.thread_name.clone();

        let handle = thread::Builder::new()
            .name(thread_name)
            .spawn(move || {
                if pin_thread {
                    // In production, pin to a dedicated core using libc::sched_setaffinity
                    // or core_affinity crate. Skipped here for portability.
                }

                Self::event_loop(dpdk_port, channel, raw_channel, stats, running)
            })?;

        self.thread_handle = Some(handle);
        Ok(())
    }

    /// The main event loop running on the dedicated thread.
    fn event_loop(
        dpdk_port: Arc<dyn DpdkPort>,
        channel: Arc<FeedChannel>,
        raw_channel: Arc<RawByteChannel>,
        stats: Arc<FeedStats>,
        running: Arc<AtomicBool>,
    ) -> FeedResult<()> {
        while running.load(Ordering::Relaxed) {
            // 1. RX burst from DPDK (kernel bypass)
            let packets = dpdk_port.rx_burst();

            if packets.is_empty() {
                // No packets — brief pause to avoid busy-wait burning CPU
                // In production, use rte_pause() or _mm_pause() instead
                std::hint::spin_loop();
                continue;
            }

            // 2. Parse and forward each packet
            for pkt in packets {
                stats.packets_received.fetch_add(1, Ordering::Relaxed);

                let local_ts = PacketParser::now_ns();

                // Forward raw bytes to raw channel (zero-copy)
                if raw_channel.try_send(pkt.clone()).is_err() {
                    stats.channel_drops.fetch_add(1, Ordering::Relaxed);
                }

                // Parse into MarketEvent
                match PacketParser::parse(&pkt, local_ts) {
                    Ok(event) => {
                        stats.events_parsed.fetch_add(1, Ordering::Relaxed);
                        stats.record_latency(event.latency_ns());

                        // Forward to downstream consumers
                        if channel.try_send(event).is_err() {
                            stats.channel_drops.fetch_add(1, Ordering::Relaxed);
                        } else {
                            stats.events_forwarded.fetch_add(1, Ordering::Relaxed);
                        }
                    }
                    Err(_) => {
                        stats.parse_errors.fetch_add(1, Ordering::Relaxed);
                    }
                }
            }
        }

        Ok(())
    }

    /// Stop the feed handler thread.
    pub fn stop(&mut self) -> FeedResult<()> {
        self.running.store(false, Ordering::SeqCst);
        if let Some(handle) = self.thread_handle.take() {
            let _ = handle
                .join()
                .map_err(|_| FeedError::Stopped);
        }
        Ok(())
    }

    /// Get a reference to the output channel.
    pub fn channel(&self) -> &FeedChannel {
        &self.channel
    }

    /// Get a reference to the raw byte channel.
    pub fn raw_channel(&self) -> &RawByteChannel {
        &self.raw_channel
    }

    /// Get current statistics.
    pub fn stats(&self) -> &FeedStats {
        &self.stats
    }

    /// Check if the handler is running.
    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::Relaxed)
    }

    /// Get a clone of the DPDK port (for mock injection in tests).
    pub fn dpdk_port(&self) -> &Arc<dyn DpdkPort> {
        &self.dpdk_port
    }
}

impl Drop for FeedHandler {
    fn drop(&mut self) {
        let _ = self.stop();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::feed_handler::protocol::HEADER_SIZE;
    use std::time::Duration;

    fn make_test_packet(id: u64) -> bytes::Bytes {
        let mut buf = vec![0u8; HEADER_SIZE];
        buf[0..8].copy_from_slice(&id.to_le_bytes());
        buf[8..16].copy_from_slice(&1000i64.to_le_bytes());
        buf[16..24].copy_from_slice(&500u64.to_le_bytes());
        buf[24] = 0;
        buf[28..32].copy_from_slice(&12345u32.to_le_bytes());
        buf[32..36].copy_from_slice(&1u32.to_le_bytes());
        buf[36..40].copy_from_slice(&0u32.to_le_bytes());
        bytes::Bytes::from(buf)
    }

    #[test]
    fn test_handler_start_stop() {
        let mut handler = FeedHandlerBuilder::new()
            .use_mock(true)
            .build()
            .unwrap();

        handler.start().unwrap();
        assert!(handler.is_running());

        handler.stop().unwrap();
        assert!(!handler.is_running());
    }

    #[test]
    fn test_handler_forwards_events() {
        let mut handler = FeedHandlerBuilder::new()
            .use_mock(true)
            .with_channel_capacity(1024)
            .build()
            .unwrap();

        handler.start().unwrap();

        // Inject packets into the mock port
        let port = handler.dpdk_port();
        if let Some(mock) = port.as_any().downcast_ref::<MockDpdkPort>() {
            for i in 0..10 {
                mock.inject_packet(make_test_packet(i)).unwrap();
            }
        }

        // Wait for processing
        thread::sleep(Duration::from_millis(100));

        // Receive events from the channel
        let mut received = 0;
        while let Ok(event) = handler.channel().try_recv() {
            assert_eq!(event.instrument_id, received);
            received += 1;
        }

        assert_eq!(received, 10);
        assert_eq!(handler.stats().events_forwarded.load(Ordering::Relaxed), 10);

        handler.stop().unwrap();
    }

    #[test]
    fn test_handler_raw_channel() {
        let mut handler = FeedHandlerBuilder::new()
            .use_mock(true)
            .build()
            .unwrap();

        handler.start().unwrap();

        let port = handler.dpdk_port();
        if let Some(mock) = port.as_any().downcast_ref::<MockDpdkPort>() {
            mock.inject_packet(make_test_packet(42)).unwrap();
        }

        thread::sleep(Duration::from_millis(50));

        let raw = handler.raw_channel().try_recv();
        assert!(raw.is_ok());
        assert_eq!(raw.unwrap().len(), HEADER_SIZE);

        handler.stop().unwrap();
    }

    #[test]
    fn test_handler_parse_error_counting() {
        let mut handler = FeedHandlerBuilder::new()
            .use_mock(true)
            .build()
            .unwrap();

        handler.start().unwrap();

        let port = handler.dpdk_port();
        if let Some(mock) = port.as_any().downcast_ref::<MockDpdkPort>() {
            // Inject a malformed packet (too short)
            mock.inject_packet(bytes::Bytes::from_static(&[0u8; 5])).unwrap();
        }

        thread::sleep(Duration::from_millis(50));

        assert_eq!(handler.stats().parse_errors.load(Ordering::Relaxed), 1);

        handler.stop().unwrap();
    }

    #[test]
    fn test_handler_channel_drop_counting() {
        let mut handler = FeedHandlerBuilder::new()
            .use_mock(true)
            .with_channel_capacity(2)
            .build()
            .unwrap();

        handler.start().unwrap();

        let port = handler.dpdk_port();
        if let Some(mock) = port.as_any().downcast_ref::<MockDpdkPort>() {
            // Inject more packets than channel capacity
            for i in 0..100 {
                mock.inject_packet(make_test_packet(i)).unwrap();
            }
        }

        thread::sleep(Duration::from_millis(200));

        // Some events should have been dropped
        assert!(handler.stats().channel_drops.load(Ordering::Relaxed) > 0);

        handler.stop().unwrap();
    }
}
