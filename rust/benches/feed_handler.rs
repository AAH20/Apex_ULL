//! Criterion benchmarks for the feed handler.
//!
//! Run with: cargo bench --bench feed_handler

use criterion::{black_box, criterion_group, criterion_main, Criterion, Throughput};
use feed_handler::channel::{FeedChannel, RawByteChannel, DEFAULT_CHANNEL_CAPACITY};
use feed_handler::protocol::{HEADER_SIZE, PacketParser};
use feed_handler::processor::FeedHandlerBuilder;
use feed_handler::types::{MarketEvent, Side};
use bytes::Bytes;
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

fn bench_packet_parse(c: &mut Criterion) {
    let packet = make_packet(42, 1_000_000_000, 500, 0);
    let local_ts = 1_000_000_000_000u64;

    let mut group = c.benchmark_group("packet_parse");
    group.throughput(Throughput::Elements(1));

    group.bench_function("parse_single", |b| {
        b.iter(|| {
            let event = PacketParser::parse(black_box(&packet), black_box(local_ts)).unwrap();
            black_box(event);
        })
    });

    group.finish();
}

fn bench_packet_parse_batch(c: &mut Criterion) {
    // Build a batch of 10 events
    let mut buf = vec![10u8];
    for i in 0..10 {
        buf.extend_from_slice(&make_packet(i, 1000 + i as i64, 100 + i as u64, (i % 2) as u8)[..]);
    }
    let batch_data = Bytes::from(buf);
    let local_ts = 1_000_000_000_000u64;

    let mut group = c.benchmark_group("packet_parse_batch");
    group.throughput(Throughput::Elements(10));

    group.bench_function("parse_batch_10", |b| {
        b.iter(|| {
            let events = PacketParser::parse_batch(black_box(&batch_data), black_box(local_ts)).unwrap();
            black_box(events);
        })
    });

    group.finish();
}

fn bench_channel_send_recv(c: &mut Criterion) {
    let channel = FeedChannel::with_default_capacity();
    let event = MarketEvent {
        instrument_id: 42,
        price: 1_000_000_000,
        quantity: 500,
        side: Side::Bid,
        exchange_ts: 12345,
        local_ts: 1_000_000_000_000,
        sequence: 1,
        raw: make_packet(42, 1_000_000_000, 500, 0),
    };

    let mut group = c.benchmark_group("channel_spsc");
    group.throughput(Throughput::Elements(1));

    group.bench_function("send_recv", |b| {
        b.iter(|| {
            channel.try_send(black_box(event.clone())).unwrap();
            let received = channel.try_recv().unwrap();
            black_box(received);
        })
    });

    group.finish();
}

fn bench_raw_channel_send_recv(c: &mut Criterion) {
    let channel = RawByteChannel::new(DEFAULT_CHANNEL_CAPACITY);
    let data = make_packet(42, 1_000_000_000, 500, 0);

    let mut group = c.benchmark_group("raw_channel_spsc");
    group.throughput(Throughput::Bytes(HEADER_SIZE as u64));

    group.bench_function("send_recv", |b| {
        b.iter(|| {
            channel.try_send(black_box(data.clone())).unwrap();
            let received = channel.try_recv().unwrap();
            black_box(received);
        })
    });

    group.finish();
}

fn bench_end_to_end_throughput(c: &mut Criterion) {
    let mut group = c.benchmark_group("end_to_end");
    group.throughput(Throughput::Elements(1));
    group.measurement_time(Duration::from_secs(5));

    group.bench_function("parse_and_forward", |b| {
        let channel = FeedChannel::with_default_capacity();
        let packet = make_packet(42, 1_000_000_000, 500, 0);

        b.iter(|| {
            let event = PacketParser::parse(black_box(&packet), black_box(0)).unwrap();
            channel.try_send(black_box(event)).unwrap();
            let received = channel.try_recv().unwrap();
            black_box(received);
        })
    });

    group.finish();
}

fn bench_handler_start_stop(c: &mut Criterion) {
    let mut group = c.benchmark_group("handler_lifecycle");

    group.bench_function("start_stop", |b| {
        b.iter(|| {
            let mut handler = FeedHandlerBuilder::new()
                .use_mock(true)
                .build()
                .unwrap();
            handler.start().unwrap();
            handler.stop().unwrap();
        })
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_packet_parse,
    bench_packet_parse_batch,
    bench_channel_send_recv,
    bench_raw_channel_send_recv,
    bench_end_to_end_throughput,
    bench_handler_start_stop,
);
criterion_main!(benches);
