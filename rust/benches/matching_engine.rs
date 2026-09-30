use criterion::{black_box, criterion_group, criterion_main, Criterion};
use crossbeam_channel::bounded;

use feed_handler::matching_engine::engine::MatchingEngine;
use feed_handler::matching_engine::types::{Order, Side};

fn bench_matching(c: &mut Criterion) {
    c.bench_function("single_order", |b| {
        b.iter(|| {
            let (tx, rx) = bounded(1);
            let (ttx, _trx) = bounded(1);
            let mut engine = MatchingEngine::new(rx, ttx);
            let order = Order { id: 1, side: Side::Buy, price: 10000, quantity: 5 };
            tx.send(black_box(order)).unwrap();
            drop(tx);
            engine.run();
        })
    });

    c.bench_function("ten_orders", |b| {
        b.iter(|| {
            let (tx, rx) = bounded(10);
            let (ttx, _trx) = bounded(10);
            let mut engine = MatchingEngine::new(rx, ttx);
            for i in 0..10 {
                tx.send(Order { id: i, side: Side::Buy, price: 10000, quantity: 1 }).unwrap();
            }
            drop(tx);
            engine.run();
        })
    });
}

criterion_group!(benches, bench_matching);
criterion_main!(benches);
