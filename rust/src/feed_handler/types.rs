//! Core market data types and error definitions.

use bytes::Bytes;
use std::fmt;
use std::sync::atomic::{AtomicU64, Ordering};
use thiserror::Error;

/// Feed handler errors.
#[derive(Debug, Error)]
pub enum FeedError {
    #[error("DPDK initialization failed: {0}")]
    DpdkInit(String),
    #[error("DPDK port configuration failed: {0}")]
    DpdkPortConfig(String),
    #[error("Invalid packet: {0}")]
    InvalidPacket(String),
    #[error("Channel send failed")]
    ChannelSend,
    #[error("Channel receive failed")]
    ChannelReceive,
    #[error("Handler stopped")]
    Stopped,
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

pub type FeedResult<T> = Result<T, FeedError>;

/// Side of a market data event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum Side {
    Bid = 0,
    Ask = 1,
}

impl Side {
    #[inline(always)]
    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0 => Some(Side::Bid),
            1 => Some(Side::Ask),
            _ => None,
        }
    }
}

impl fmt::Display for Side {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Side::Bid => write!(f, "BID"),
            Side::Ask => write!(f, "ASK"),
        }
    }
}

/// A single market data event parsed from the wire.
///
/// Zero-copy: `raw` holds the original packet bytes; all other fields
/// are parsed views into that buffer.
#[derive(Debug, Clone)]
pub struct MarketEvent {
    /// Instrument ID (e.g., ticker symbol hash).
    pub instrument_id: u64,
    /// Price in fixed-point (multiply by 1e-9 for decimal).
    pub price: i64,
    /// Quantity.
    pub quantity: u64,
    /// Side (bid/ask).
    pub side: Side,
    /// Exchange timestamp in nanoseconds since epoch.
    pub exchange_ts: u64,
    /// Local receive timestamp in nanoseconds since epoch.
    pub local_ts: u64,
    /// Sequence number for gap detection.
    pub sequence: u64,
    /// Zero-copy reference to the raw packet bytes.
    pub raw: Bytes,
}

impl MarketEvent {
    /// Latency from exchange timestamp to local receive timestamp (nanoseconds).
    #[inline(always)]
    pub fn latency_ns(&self) -> u64 {
        self.local_ts.saturating_sub(self.exchange_ts)
    }
}

/// Statistics for the feed handler.
///
/// All fields are atomic for lock-free concurrent access.
#[derive(Debug, Default)]
pub struct FeedStats {
    pub packets_received: AtomicU64,
    pub events_parsed: AtomicU64,
    pub events_forwarded: AtomicU64,
    pub parse_errors: AtomicU64,
    pub channel_drops: AtomicU64,
    total_latency_ns: AtomicU64,
    min_latency_ns: AtomicU64,
    max_latency_ns: AtomicU64,
}

impl FeedStats {
    pub fn new() -> Self {
        Self {
            min_latency_ns: AtomicU64::new(u64::MAX),
            ..Default::default()
        }
    }

    #[inline(always)]
    pub fn record_latency(&self, latency_ns: u64) {
        self.total_latency_ns
            .fetch_add(latency_ns, Ordering::Relaxed);

        // Update min
        let mut current_min = self.min_latency_ns.load(Ordering::Relaxed);
        while latency_ns < current_min {
            match self.min_latency_ns.compare_exchange_weak(
                current_min,
                latency_ns,
                Ordering::Relaxed,
                Ordering::Relaxed,
            ) {
                Ok(_) => break,
                Err(actual) => current_min = actual,
            }
        }

        // Update max
        let mut current_max = self.max_latency_ns.load(Ordering::Relaxed);
        while latency_ns > current_max {
            match self.max_latency_ns.compare_exchange_weak(
                current_max,
                latency_ns,
                Ordering::Relaxed,
                Ordering::Relaxed,
            ) {
                Ok(_) => break,
                Err(actual) => current_max = actual,
            }
        }
    }

    pub fn avg_latency_ns(&self) -> u64 {
        let count = self.events_forwarded.load(Ordering::Relaxed);
        if count == 0 {
            0
        } else {
            self.total_latency_ns.load(Ordering::Relaxed) / count
        }
    }

    pub fn min_latency_ns(&self) -> u64 {
        let v = self.min_latency_ns.load(Ordering::Relaxed);
        if v == u64::MAX {
            0
        } else {
            v
        }
    }

    pub fn max_latency_ns(&self) -> u64 {
        self.max_latency_ns.load(Ordering::Relaxed)
    }

    pub fn snapshot(&self) -> FeedStatsSnapshot {
        FeedStatsSnapshot {
            packets_received: self.packets_received.load(Ordering::Relaxed),
            events_parsed: self.events_parsed.load(Ordering::Relaxed),
            events_forwarded: self.events_forwarded.load(Ordering::Relaxed),
            parse_errors: self.parse_errors.load(Ordering::Relaxed),
            channel_drops: self.channel_drops.load(Ordering::Relaxed),
            total_latency_ns: self.total_latency_ns.load(Ordering::Relaxed),
            min_latency_ns: self.min_latency_ns(),
            max_latency_ns: self.max_latency_ns(),
        }
    }
}

/// A consistent snapshot of feed statistics.
#[derive(Debug, Default, Clone, Copy)]
pub struct FeedStatsSnapshot {
    pub packets_received: u64,
    pub events_parsed: u64,
    pub events_forwarded: u64,
    pub parse_errors: u64,
    pub channel_drops: u64,
    pub total_latency_ns: u64,
    pub min_latency_ns: u64,
    pub max_latency_ns: u64,
}

impl FeedStatsSnapshot {
    pub fn avg_latency_ns(&self) -> u64 {
        if self.events_forwarded == 0 {
            0
        } else {
            self.total_latency_ns / self.events_forwarded
        }
    }
}
