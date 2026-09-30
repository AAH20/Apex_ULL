use std::collections::{BTreeMap, VecDeque};

use crate::matching_engine::types::{Order, OrderId, Price, Quantity, Side, Trade};

/// Price-time priority order book using BTreeMap.
pub struct OrderBook {
    bids: BTreeMap<Price, VecDeque<OrderId>>,
    asks: BTreeMap<Price, VecDeque<OrderId>>,
    pub(crate) orders: BTreeMap<OrderId, Order>,
}

impl OrderBook {
    #[inline]
    pub fn new() -> Self {
        Self { bids: BTreeMap::new(), asks: BTreeMap::new(), orders: BTreeMap::new() }
    }

    #[inline]
    pub fn add(&mut self, order: Order) {
        let side_map = if order.side == Side::Buy { &mut self.bids } else { &mut self.asks };
        side_map.entry(order.price).or_default().push_back(order.id);
        self.orders.insert(order.id, order);
    }

    /// Match an incoming order against the opposite side.
    /// Returns (filled_qty, remaining_qty, trades).
    pub fn match_order(
        &mut self,
        incoming: &mut Order,
    ) -> (Quantity, Quantity, Vec<Trade>) {
        let mut filled = 0;
        let mut trades = Vec::new();
        let opposite = if incoming.side == Side::Buy { &mut self.asks } else { &mut self.bids };

        while incoming.quantity > 0 {
            let best_price = match Self::best_key(opposite, incoming.side) {
                Some(p) if Self::cross(incoming.price, p, incoming.side) => p,
                _ => break,
            };

            let queue = opposite.get_mut(&best_price).unwrap();
            let mut i = 0;
            while i < queue.len() && incoming.quantity > 0 {
                let maker_id = queue[i];
                let maker = self.orders.get_mut(&maker_id).unwrap();
                let qty = incoming.quantity.min(maker.quantity);
                maker.quantity -= qty;
                incoming.quantity -= qty;
                filled += qty;

                trades.push(Trade {
                    maker_id,
                    taker_id: incoming.id,
                    price: best_price,
                    quantity: qty,
                });

                if maker.quantity == 0 {
                    self.orders.remove(&maker_id);
                    queue.remove(i);
                } else {
                    i += 1;
                }
            }

            if queue.is_empty() {
                opposite.remove(&best_price);
            }
        }

        (filled, incoming.quantity, trades)
    }

    #[inline]
    fn best_key(map: &BTreeMap<Price, VecDeque<OrderId>>, side: Side) -> Option<Price> {
        if side == Side::Buy { map.keys().next().copied() } else { map.keys().next_back().copied() }
    }

    #[inline]
    fn cross(taker: Price, maker: Price, side: Side) -> bool {
        if side == Side::Buy { taker >= maker } else { taker <= maker }
    }
}

impl Default for OrderBook {
    fn default() -> Self { Self::new() }
}
