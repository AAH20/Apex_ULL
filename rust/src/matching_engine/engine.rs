use crossbeam_channel::{bounded, Receiver, Sender};

use crate::matching_engine::order_book::OrderBook;
use crate::matching_engine::types::{Order, Trade};

/// Matching engine driven by crossbeam SPSC channels.
pub struct MatchingEngine {
    rx: Receiver<Order>,
    trade_tx: Sender<Trade>,
    pub(crate) book: OrderBook,
}

impl MatchingEngine {
    pub fn new(rx: Receiver<Order>, trade_tx: Sender<Trade>) -> Self {
        Self { rx, trade_tx, book: OrderBook::new() }
    }

    pub fn run(&mut self) {
        while let Ok(mut order) = self.rx.recv() {
            let (_, remaining, trades) = self.book.match_order(&mut order);
            if remaining > 0 {
                self.book.add(order);
            }
            for t in &trades {
                let _ = self.trade_tx.send(*t);
            }
        }
    }
}

/// Spawn an engine on a dedicated thread.
pub fn spawn_engine() -> (Sender<Order>, Receiver<Trade>) {
    let (order_tx, order_rx) = bounded(4096);
    let (trade_tx, trade_rx) = bounded(4096);
    std::thread::spawn(move || {
        MatchingEngine::new(order_rx, trade_tx).run();
    });
    (order_tx, trade_rx)
}
