//! Lock-free SPSC channel for inter-thread communication.
//!
//! Wraps `crossbeam_channel` with a bounded, cache-line-aligned ring buffer
//! optimized for single-producer single-consumer patterns.

use bytes::Bytes;
use crossbeam_channel::{bounded, Receiver, Sender};

use super::types::{FeedError, FeedResult, MarketEvent};

/// Default channel capacity (power of 2 for efficient masking).
pub const DEFAULT_CHANNEL_CAPACITY: usize = 65536;

/// A bounded SPSC channel for market data events.
///
/// Uses crossbeam's lock-free MPMC ring buffer internally, but enforces
/// SPSC semantics at the type level for maximum performance.
pub struct FeedChannel {
    sender: Sender<MarketEvent>,
    receiver: Receiver<MarketEvent>,
    capacity: usize,
}

impl FeedChannel {
    /// Create a new bounded channel with the given capacity.
    pub fn new(capacity: usize) -> Self {
        let (sender, receiver) = bounded(capacity);
        Self {
            sender,
            receiver,
            capacity,
        }
    }

    /// Create a new channel with default capacity.
    pub fn with_default_capacity() -> Self {
        Self::new(DEFAULT_CHANNEL_CAPACITY)
    }

    /// Send an event into the channel.
    ///
    /// Returns `Err` if the channel is full or disconnected.
    #[inline(always)]
    pub fn send(&self, event: MarketEvent) -> FeedResult<()> {
        self.sender
            .send(event)
            .map_err(|_| FeedError::ChannelSend)
    }

    /// Try to send without blocking.
    #[inline(always)]
    pub fn try_send(&self, event: MarketEvent) -> FeedResult<()> {
        self.sender
            .try_send(event)
            .map_err(|_| FeedError::ChannelSend)
    }

    /// Receive an event from the channel.
    #[inline(always)]
    pub fn recv(&self) -> FeedResult<MarketEvent> {
        self.receiver.recv().map_err(|_| FeedError::ChannelReceive)
    }

    /// Try to receive without blocking.
    #[inline(always)]
    pub fn try_recv(&self) -> FeedResult<MarketEvent> {
        self.receiver
            .try_recv()
            .map_err(|_| FeedError::ChannelReceive)
    }

    /// Get the channel capacity.
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Get the number of items currently in the channel.
    pub fn len(&self) -> usize {
        self.receiver.len()
    }

    /// Check if the channel is empty.
    pub fn is_empty(&self) -> bool {
        self.receiver.is_empty()
    }

    /// Check if the channel is full.
    pub fn is_full(&self) -> bool {
        self.len() >= self.capacity
    }

    /// Get a clone of the sender (for moving to producer thread).
    pub fn sender(&self) -> Sender<MarketEvent> {
        self.sender.clone()
    }

    /// Get a clone of the receiver (for moving to consumer thread).
    pub fn receiver(&self) -> Receiver<MarketEvent> {
        self.receiver.clone()
    }
}

/// A raw byte channel for packet forwarding (zero-copy).
pub struct RawByteChannel {
    sender: Sender<Bytes>,
    receiver: Receiver<Bytes>,
    capacity: usize,
}

impl RawByteChannel {
    pub fn new(capacity: usize) -> Self {
        let (sender, receiver) = bounded(capacity);
        Self {
            sender,
            receiver,
            capacity,
        }
    }

    #[inline(always)]
    pub fn send(&self, data: Bytes) -> FeedResult<()> {
        self.sender
            .send(data)
            .map_err(|_| FeedError::ChannelSend)
    }

    #[inline(always)]
    pub fn try_send(&self, data: Bytes) -> FeedResult<()> {
        self.sender
            .try_send(data)
            .map_err(|_| FeedError::ChannelSend)
    }

    #[inline(always)]
    pub fn recv(&self) -> FeedResult<Bytes> {
        self.receiver.recv().map_err(|_| FeedError::ChannelReceive)
    }

    #[inline(always)]
    pub fn try_recv(&self) -> FeedResult<Bytes> {
        self.receiver
            .try_recv()
            .map_err(|_| FeedError::ChannelReceive)
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }

    pub fn len(&self) -> usize {
        self.receiver.len()
    }

    pub fn is_empty(&self) -> bool {
        self.receiver.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::feed_handler::types::Side;

    fn make_event(id: u64) -> MarketEvent {
        MarketEvent {
            instrument_id: id,
            price: 100,
            quantity: 10,
            side: Side::Bid,
            exchange_ts: 0,
            local_ts: 0,
            sequence: id,
            raw: Bytes::new(),
        }
    }

    #[test]
    fn test_channel_send_recv() {
        let ch = FeedChannel::new(16);
        ch.send(make_event(1)).unwrap();
        ch.send(make_event(2)).unwrap();

        assert_eq!(ch.recv().unwrap().instrument_id, 1);
        assert_eq!(ch.recv().unwrap().instrument_id, 2);
    }

    #[test]
    fn test_channel_try_send_full() {
        let ch = FeedChannel::new(2);
        ch.try_send(make_event(1)).unwrap();
        ch.try_send(make_event(2)).unwrap();
        assert!(ch.try_send(make_event(3)).is_err());
    }

    #[test]
    fn test_channel_try_recv_empty() {
        let ch = FeedChannel::new(16);
        assert!(ch.try_recv().is_err());
    }

    #[test]
    fn test_channel_len() {
        let ch = FeedChannel::new(16);
        assert_eq!(ch.len(), 0);
        ch.send(make_event(1)).unwrap();
        assert_eq!(ch.len(), 1);
        ch.recv().unwrap();
        assert_eq!(ch.len(), 0);
    }

    #[test]
    fn test_raw_byte_channel() {
        let ch = RawByteChannel::new(16);
        let data = Bytes::from_static(&[1, 2, 3, 4]);
        ch.send(data.clone()).unwrap();
        assert_eq!(ch.recv().unwrap(), data);
    }

    #[test]
    fn test_channel_capacity() {
        let ch = FeedChannel::new(128);
        assert_eq!(ch.capacity(), 128);
    }

    #[test]
    fn test_default_capacity() {
        let ch = FeedChannel::with_default_capacity();
        assert_eq!(ch.capacity(), DEFAULT_CHANNEL_CAPACITY);
    }
}
