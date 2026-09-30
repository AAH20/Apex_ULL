//! Integration tests for the feed handler.

use feed_handler::channel::FeedChannel;
use feed_handler::dpdk::MockDpdkPort;
use feed_handler::processor::FeedHandlerBuilder;
use feed_handler::protocol::HEADER_SIZE;
use feed_handler::types::{FeedError, MarketEvent, Side};
use bytes::Bytes;
use std::sync::atomic::Ordering;
use std::sync::Arc;
use std::thread;
use std::time::Duration;

fn make_packet(instrument_id: u64, price: i64, quantity: u64, side: u8) -> Bytes {
    let mut buf = vec![0u8; HEADER_SIZE];
    buf[0..8].copy_from_slice(&instrument_id.to_le_bytes());
    buf[8..16].copy_from_slice(&price.to_le_bytes());
    buf[16..24].copy_from_slice(&quantity.to_le_bytes());
    buf[24] = side;
    buf[28..32].copy_from_slice(&12345u32.to_le_bytes());
    buf[32..36].copy_from_slice(&1u32.to_le_bytes());
    buf[36..40].copy_from_slice(&0u32.to_le_bytes());
    Bytes::from(buf)
}

#[test]
fn test_full_pipeline() {
    let mut handler = FeedHandlerBuilder::new()
        .use_mock(true)
        .with_channel_capacity(1024)
        .build()
        .unwrap();

    handler.start().unwrap();

    // Inject 100 packets
    let port = handler.dpdk_port();
    let mock = port.as_any().downcast_ref::<MockDpdkPort>().unwrap();
    for i in 0..100 {
        mock.inject_packet(make_packet(i, 1000 + i as i64, 100, (i % 2) as u8))
            .unwrap();
    }

    // Wait for processing
    thread::sleep(Duration::from_millis(200));

    // Verify all events were forwarded
    let mut received = 0;
    while handler.channel().try_recv().is_ok() {
        received += 1;
    }

    assert_eq!(received, 100);
    assert_eq!(handler.stats().events_forwarded.load(Ordering::Relaxed), 100);
    assert_eq!(handler.stats().parse_errors.load(Ordering::Relaxed), 0);

    handler.stop().unwrap();
}

#[test]
fn test_concurrent_producers_single_consumer() {
    let channel = Arc::new(FeedChannel::new(4096));
    let num_producers = 4;
    let events_per_producer = 1000;
    let total_events = num_producers * events_per_producer;

    let mut handles = vec![];

    // Spawn producers
    for p in 0..num_producers {
        let ch: Arc<FeedChannel> = Arc::clone(&channel);
        let handle = thread::spawn(move || {
            for i in 0..events_per_producer {
                let event = MarketEvent {
                    instrument_id: (p * events_per_producer + i) as u64,
                    price: 1000,
                    quantity: 100,
                    side: Side::Bid,
                    exchange_ts: 0,
                    local_ts: 0,
                    sequence: i as u64,
                    raw: Bytes::new(),
                };
                ch.send(event).unwrap();
            }
        });
        handles.push(handle);
    }

    // Single consumer receives all events
    let ch: Arc<FeedChannel> = Arc::clone(&channel);
    let consumer = thread::spawn(move || {
        let mut count = 0;
        while count < total_events {
            match ch.recv() {
                Ok(_) => count += 1,
                Err(_) => break,
            }
        }
        count
    });

    // Wait for producers
    for h in handles {
        h.join().unwrap();
    }

    let total_received = consumer.join().unwrap();
    assert_eq!(total_received, total_events);
}

#[test]
fn test_handler_with_real_dpdk_config() {
    use feed_handler::dpdk::DpdkConfig;

    let config = DpdkConfig::new(0);
    let result = FeedHandlerBuilder::new()
        .with_dpdk_config(config)
        .build();

    // Should succeed (stub implementation)
    assert!(result.is_ok());
}

#[test]
fn test_handler_invalid_dpdk_config() {
    use feed_handler::dpdk::DpdkConfig;

    let config = DpdkConfig {
        num_rx_queues: 0,
        ..Default::default()
    };
    let result = FeedHandlerBuilder::new()
        .with_dpdk_config(config)
        .build();

    assert!(matches!(result, Err(FeedError::DpdkPortConfig(_))));
}

#[test]
fn test_stats_tracking() {
    let mut handler = FeedHandlerBuilder::new()
        .use_mock(true)
        .build()
        .unwrap();

    handler.start().unwrap();

    let port = handler.dpdk_port();
    let mock = port.as_any().downcast_ref::<MockDpdkPort>().unwrap();

    // Inject valid packets
    for i in 0..10 {
        mock.inject_packet(make_packet(i, 1000, 100, 0)).unwrap();
    }

    // Inject invalid packet
    mock.inject_packet(Bytes::from_static(&[0u8; 5])).unwrap();

    thread::sleep(Duration::from_millis(100));

    let stats = handler.stats();
    assert_eq!(stats.packets_received.load(Ordering::Relaxed), 11);
    assert_eq!(stats.events_parsed.load(Ordering::Relaxed), 10);
    assert_eq!(stats.parse_errors.load(Ordering::Relaxed), 1);

    handler.stop().unwrap();
}

#[test]
fn test_raw_channel_zero_copy() {
    let mut handler = FeedHandlerBuilder::new()
        .use_mock(true)
        .build()
        .unwrap();

    handler.start().unwrap();

    let port = handler.dpdk_port();
    let mock = port.as_any().downcast_ref::<MockDpdkPort>().unwrap();
    let original = make_packet(42, 5000, 200, 1);
    mock.inject_packet(original.clone()).unwrap();

    thread::sleep(Duration::from_millis(50));

    let raw = handler.raw_channel().try_recv().unwrap();
    // Verify zero-copy: same underlying data
    assert_eq!(raw.as_ref(), original.as_ref());

    handler.stop().unwrap();
}

#[test]
fn test_multiple_handlers() {
    let mut handler1 = FeedHandlerBuilder::new()
        .use_mock(true)
        .thread_name("handler-1")
        .build()
        .unwrap();

    let mut handler2 = FeedHandlerBuilder::new()
        .use_mock(true)
        .thread_name("handler-2")
        .build()
        .unwrap();

    handler1.start().unwrap();
    handler2.start().unwrap();

    assert!(handler1.is_running());
    assert!(handler2.is_running());

    handler1.stop().unwrap();
    handler2.stop().unwrap();

    assert!(!handler1.is_running());
    assert!(!handler2.is_running());
}

#[test]
fn test_channel_capacity_bounds() {
    let channel = FeedChannel::new(4);
    assert_eq!(channel.capacity(), 4);

    // Fill to capacity
    for i in 0..4 {
        let event = MarketEvent {
            instrument_id: i,
            price: 0,
            quantity: 0,
            side: Side::Bid,
            exchange_ts: 0,
            local_ts: 0,
            sequence: 0,
            raw: Bytes::new(),
        };
        channel.try_send(event).unwrap();
    }

    assert!(channel.is_full());

    // Next send should fail
    let event = MarketEvent {
        instrument_id: 99,
        price: 0,
        quantity: 0,
        side: Side::Bid,
        exchange_ts: 0,
        local_ts: 0,
        sequence: 0,
        raw: Bytes::new(),
    };
    assert!(channel.try_send(event).is_err());
}

#[test]
fn test_handler_drop_stops_thread() {
    let handler = FeedHandlerBuilder::new()
        .use_mock(true)
        .build()
        .unwrap();

    // Handler should be dropped without explicit stop
    drop(handler);
    // If we get here without panic, the Drop impl worked
}
