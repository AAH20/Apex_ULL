//! Zero-copy binary protocol parser for market data packets.
//!
//! Wire format (little-endian, 40-byte fixed header + variable payload):
//!
//! ```text
//! Offset  Size  Field
//! 0       8     instrument_id (u64)
//! 8       8     price (i64, fixed-point)
//! 16      8     quantity (u64)
//! 24      1     side (u8: 0=bid, 1=ask)
//! 25      3     reserved
//! 28      4     exchange_ts (u32, nanoseconds since midnight UTC)
//! 32      4     sequence (u32)
//! 36      4     payload_len (u32)
//! 40      N     payload (variable)
//! ```
//!
//! Total header: 40 bytes. Maximum packet: 40 + 65536 bytes.

use bytes::Bytes;
use std::time::{SystemTime, UNIX_EPOCH};

use super::types::{FeedError, FeedResult, MarketEvent, Side};

/// Size of the fixed packet header in bytes.
pub const HEADER_SIZE: usize = 40;
/// Maximum payload size in bytes.
pub const MAX_PAYLOAD_SIZE: usize = 65536;
/// Maximum total packet size in bytes.
pub const MAX_PACKET_SIZE: usize = HEADER_SIZE + MAX_PAYLOAD_SIZE;

/// A zero-copy packet parser.
///
/// Parses raw bytes into `MarketEvent` without allocating — all fields
/// are views into the original `Bytes` buffer.
pub struct PacketParser;

impl PacketParser {
    /// Parse a single packet into a `MarketEvent`.
    ///
    /// # Arguments
    /// * `data` - Raw packet bytes (must be at least `HEADER_SIZE` bytes)
    /// * `local_ts` - Local receive timestamp in nanoseconds since epoch
    ///
    /// # Returns
    /// * `Ok(MarketEvent)` on success
    /// * `Err(FeedError)` if the packet is malformed
    #[inline]
    pub fn parse(data: &Bytes, local_ts: u64) -> FeedResult<MarketEvent> {
        if data.len() < HEADER_SIZE {
            return Err(FeedError::InvalidPacket(format!(
                "packet too short: {} bytes (min {})",
                data.len(),
                HEADER_SIZE
            )));
        }

        // SAFETY: We checked data.len() >= HEADER_SIZE above.
        let instrument_id = u64::from_le_bytes(data[0..8].try_into().unwrap());
        let price = i64::from_le_bytes(data[8..16].try_into().unwrap());
        let quantity = u64::from_le_bytes(data[16..24].try_into().unwrap());
        let side = Side::from_u8(data[24])
            .ok_or_else(|| FeedError::InvalidPacket(format!("invalid side byte: {}", data[24])))?;
        let exchange_ts = u32::from_le_bytes(data[28..32].try_into().unwrap()) as u64;
        let sequence = u32::from_le_bytes(data[32..36].try_into().unwrap()) as u64;
        let payload_len = u32::from_le_bytes(data[36..40].try_into().unwrap()) as usize;

        if payload_len > MAX_PAYLOAD_SIZE {
            return Err(FeedError::InvalidPacket(format!(
                "payload too large: {} bytes (max {})",
                payload_len, MAX_PAYLOAD_SIZE
            )));
        }

        if data.len() < HEADER_SIZE + payload_len {
            return Err(FeedError::InvalidPacket(format!(
                "packet truncated: {} bytes, expected {}",
                data.len(),
                HEADER_SIZE + payload_len
            )));
        }

        Ok(MarketEvent {
            instrument_id,
            price,
            quantity,
            side,
            exchange_ts,
            local_ts,
            sequence,
            raw: data.clone(),
        })
    }

    /// Parse multiple events from a single packet (multicast batch).
    ///
    /// Batch format: `[count: u8][event1][event2]...[eventN]`
    /// Each event is `HEADER_SIZE` bytes (no payload in batch mode).
    #[inline]
    pub fn parse_batch(data: &Bytes, local_ts: u64) -> FeedResult<Vec<MarketEvent>> {
        if data.is_empty() {
            return Ok(Vec::new());
        }

        let count = data[0] as usize;
        let mut events = Vec::with_capacity(count);
        let mut offset = 1usize;

        for _ in 0..count {
            if offset + HEADER_SIZE > data.len() {
                return Err(FeedError::InvalidPacket(
                    "batch packet truncated".to_string(),
                ));
            }
            let event_data = data.slice(offset..offset + HEADER_SIZE);
            let event = Self::parse(&event_data, local_ts)?;
            events.push(event);
            offset += HEADER_SIZE;
        }

        Ok(events)
    }

    /// Get the current timestamp in nanoseconds since epoch.
    #[inline(always)]
    pub fn now_ns() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos() as u64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_packet(
        instrument_id: u64,
        price: i64,
        quantity: u64,
        side: u8,
        exchange_ts: u32,
        sequence: u32,
    ) -> Bytes {
        let mut buf = vec![0u8; HEADER_SIZE];
        buf[0..8].copy_from_slice(&instrument_id.to_le_bytes());
        buf[8..16].copy_from_slice(&price.to_le_bytes());
        buf[16..24].copy_from_slice(&quantity.to_le_bytes());
        buf[24] = side;
        buf[28..32].copy_from_slice(&exchange_ts.to_le_bytes());
        buf[32..36].copy_from_slice(&sequence.to_le_bytes());
        buf[36..40].copy_from_slice(&0u32.to_le_bytes()); // payload_len = 0
        Bytes::from(buf)
    }

    #[test]
    fn test_parse_valid_packet() {
        let data = make_packet(42, 1000000000, 500, 0, 1234567890, 1);
        let local_ts = 1_000_000_000_000;
        let event = PacketParser::parse(&data, local_ts).unwrap();

        assert_eq!(event.instrument_id, 42);
        assert_eq!(event.price, 1_000_000_000);
        assert_eq!(event.quantity, 500);
        assert_eq!(event.side, Side::Bid);
        assert_eq!(event.exchange_ts, 1_234_567_890);
        assert_eq!(event.sequence, 1);
        assert_eq!(event.local_ts, local_ts);
    }

    #[test]
    fn test_parse_ask_side() {
        let data = make_packet(1, 2500000000, 100, 1, 0, 2);
        let event = PacketParser::parse(&data, 0).unwrap();
        assert_eq!(event.side, Side::Ask);
    }

    #[test]
    fn test_parse_too_short() {
        let data = Bytes::from_static(&[0u8; 10]);
        let result = PacketParser::parse(&data, 0);
        assert!(matches!(result, Err(FeedError::InvalidPacket(_))));
    }

    #[test]
    fn test_parse_invalid_side() {
        let data = make_packet(1, 0, 0, 2, 0, 0);
        let result = PacketParser::parse(&data, 0);
        assert!(matches!(result, Err(FeedError::InvalidPacket(_))));
    }

    #[test]
    fn test_parse_batch() {
        let mut buf = vec![2u8]; // count = 2
        buf.extend_from_slice(&make_packet(1, 100, 10, 0, 0, 1)[..]);
        buf.extend_from_slice(&make_packet(2, 200, 20, 1, 0, 2)[..]);
        let data = Bytes::from(buf);

        let events = PacketParser::parse_batch(&data, 12345).unwrap();
        assert_eq!(events.len(), 2);
        assert_eq!(events[0].instrument_id, 1);
        assert_eq!(events[1].instrument_id, 2);
    }

    #[test]
    fn test_parse_empty_batch() {
        let data = Bytes::new();
        let events = PacketParser::parse_batch(&data, 0).unwrap();
        assert!(events.is_empty());
    }

    #[test]
    fn test_latency_calculation() {
        let data = make_packet(1, 0, 0, 0, 0, 0);
        let event = PacketParser::parse(&data, 1000).unwrap();
        assert_eq!(event.latency_ns(), 1000);
    }

    #[test]
    fn test_zero_copy() {
        let data = make_packet(99, 12345, 67890, 1, 111, 222);
        let event = PacketParser::parse(&data, 0).unwrap();
        // The raw field should share the same underlying allocation
        assert_eq!(event.raw.len(), data.len());
        assert_eq!(event.raw.as_ref(), data.as_ref());
    }
}
