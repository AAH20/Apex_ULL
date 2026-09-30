#[cfg(test)]
mod tests {
    use crossbeam_channel::bounded;

    use crate::matching_engine::engine::MatchingEngine;
    use crate::matching_engine::order_book::OrderBook;
    use crate::matching_engine::types::{Order, Side};

    #[test]
    fn buy_crosses_sell() {
        let (tx, rx) = bounded(1);
        let (ttx, _trx) = bounded(1);
        let mut engine = MatchingEngine::new(rx, ttx);

        tx.send(Order { id: 1, side: Side::Sell, price: 9000, quantity: 5 }).unwrap();
        drop(tx);
        engine.run();

        let (_, remaining, trades) = engine.book.match_order(&mut Order {
            id: 2, side: Side::Buy, price: 10000, quantity: 3,
        });
        assert_eq!(remaining, 0);
        assert_eq!(trades.len(), 1);
        assert_eq!(trades[0].quantity, 3);
        assert_eq!(trades[0].price, 9000);
    }

    #[test]
    fn partial_fill() {
        let mut book = OrderBook::new();
        book.add(Order { id: 1, side: Side::Sell, price: 10000, quantity: 10 });

        let (filled, remaining, trades) = book.match_order(&mut Order {
            id: 2, side: Side::Buy, price: 10000, quantity: 3,
        });
        assert_eq!(filled, 3);
        assert_eq!(remaining, 0);
        assert_eq!(trades.len(), 1);
        assert_eq!(trades[0].quantity, 3);
    }

    #[test]
    fn no_cross() {
        let mut book = OrderBook::new();
        book.add(Order { id: 1, side: Side::Sell, price: 11000, quantity: 5 });

        let (filled, remaining, trades) = book.match_order(&mut Order {
            id: 2, side: Side::Buy, price: 10000, quantity: 5,
        });
        assert_eq!(filled, 0);
        assert_eq!(remaining, 5);
        assert!(trades.is_empty());
    }

    #[test]
    fn price_time_priority() {
        let mut book = OrderBook::new();
        book.add(Order { id: 1, side: Side::Sell, price: 9000, quantity: 3 });
        book.add(Order { id: 2, side: Side::Sell, price: 9000, quantity: 2 });

        let (_, _, trades) = book.match_order(&mut Order {
            id: 3, side: Side::Buy, price: 10000, quantity: 5,
        });
        assert_eq!(trades.len(), 2);
        assert_eq!(trades[0].maker_id, 1);
        assert_eq!(trades[1].maker_id, 2);
    }

    #[test]
    fn best_price_first() {
        let mut book = OrderBook::new();
        book.add(Order { id: 1, side: Side::Sell, price: 9500, quantity: 2 });
        book.add(Order { id: 2, side: Side::Sell, price: 9000, quantity: 2 });

        let (_, _, trades) = book.match_order(&mut Order {
            id: 3, side: Side::Buy, price: 10000, quantity: 3,
        });
        assert_eq!(trades[0].price, 9000);
        assert_eq!(trades[1].price, 9500);
    }

    #[test]
    fn run_consumes_all_orders() {
        let (tx, rx) = bounded(10);
        let (ttx, _trx) = bounded(10);
        let mut engine = MatchingEngine::new(rx, ttx);

        for i in 1..=5 {
            tx.send(Order { id: i, side: Side::Buy, price: 10000, quantity: 1 }).unwrap();
        }
        drop(tx);
        engine.run();
        assert_eq!(engine.book.orders.len(), 5);
    }
}
