/// Fixed-point price: 1 unit = 0.0001.
pub type Price = i64;
pub type Quantity = u64;
pub type OrderId = u64;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum Side {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Copy)]
pub struct Order {
    pub id: OrderId,
    pub side: Side,
    pub price: Price,
    pub quantity: Quantity,
}

#[derive(Debug, Clone, Copy)]
pub struct Trade {
    pub maker_id: OrderId,
    pub taker_id: OrderId,
    pub price: Price,
    pub quantity: Quantity,
}
