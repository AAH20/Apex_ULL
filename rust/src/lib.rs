//! Ultra-low-latency market data feed handler.
//!
//! Architecture:
//! - DPDK kernel bypass for NIC packet reception (zero-copy from NIC to userspace)
//! - Crossbeam SPSC channels for lock-free inter-thread communication
//! - Zero-copy binary protocol parsing using `bytes::Bytes`
//! - Target: <5µs p50, <10µs p99 end-to-end latency

pub mod feed_handler;
pub mod matching_engine;

// Re-export submodules at crate root for ergonomic imports
pub use feed_handler::channel;
pub use feed_handler::dpdk;
pub use feed_handler::processor;
pub use feed_handler::protocol;
pub use feed_handler::types;

pub use channel::FeedChannel;
pub use processor::{FeedHandler, FeedHandlerBuilder};
pub use types::{FeedError, FeedResult, FeedStats, MarketEvent, Side};
