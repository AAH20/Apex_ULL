#pragma once

#include <cstdint>
#include <string>

namespace matching_engine {

/// Fixed-point price with 4 decimal places (scale = 10000).
/// Range: ±922,337,203.68 with 0.0001 precision.
class Price {
public:
    static constexpr int64_t kScale = 10000;

    constexpr Price() = default;
    constexpr explicit Price(int64_t raw) : raw_(raw) {}
    constexpr Price(double d) : raw_(static_cast<int64_t>(d * kScale + (d >= 0 ? 0.5 : -0.5))) {}

    [[nodiscard]] constexpr int64_t raw() const noexcept { return raw_; }
    [[nodiscard]] constexpr double to_double() const noexcept { return static_cast<double>(raw_) / kScale; }

    [[nodiscard]] constexpr Price operator+(Price rhs) const noexcept { return Price(raw_ + rhs.raw_); }
    [[nodiscard]] constexpr Price operator-(Price rhs) const noexcept { return Price(raw_ - rhs.raw_); }
    [[nodiscard]] constexpr bool operator==(Price rhs) const noexcept { return raw_ == rhs.raw_; }
    [[nodiscard]] constexpr bool operator!=(Price rhs) const noexcept { return raw_ != rhs.raw_; }
    [[nodiscard]] constexpr bool operator<(Price rhs) const noexcept { return raw_ < rhs.raw_; }
    [[nodiscard]] constexpr bool operator>(Price rhs) const noexcept { return raw_ > rhs.raw_; }
    [[nodiscard]] constexpr bool operator<=(Price rhs) const noexcept { return raw_ <= rhs.raw_; }
    [[nodiscard]] constexpr bool operator>=(Price rhs) const noexcept { return raw_ >= rhs.raw_; }

private:
    int64_t raw_{0};
};

/// Fixed-point quantity with 4 decimal places.
class Quantity {
public:
    static constexpr int64_t kScale = 10000;

    constexpr Quantity() = default;
    constexpr explicit Quantity(int64_t raw) : raw_(raw) {}
    constexpr Quantity(double d) : raw_(static_cast<int64_t>(d * kScale + (d >= 0 ? 0.5 : -0.5))) {}

    [[nodiscard]] constexpr int64_t raw() const noexcept { return raw_; }
    [[nodiscard]] constexpr double to_double() const noexcept { return static_cast<double>(raw_) / kScale; }

    [[nodiscard]] constexpr Quantity operator-(Quantity rhs) const noexcept { return Quantity(raw_ - rhs.raw_); }
    [[nodiscard]] constexpr bool operator==(Quantity rhs) const noexcept { return raw_ == rhs.raw_; }
    [[nodiscard]] constexpr bool operator!=(Quantity rhs) const noexcept { return raw_ != rhs.raw_; }
    [[nodiscard]] constexpr bool operator<(Quantity rhs) const noexcept { return raw_ < rhs.raw_; }
    [[nodiscard]] constexpr bool operator>(Quantity rhs) const noexcept { return raw_ > rhs.raw_; }
    [[nodiscard]] constexpr bool operator<=(Quantity rhs) const noexcept { return raw_ <= rhs.raw_; }
    [[nodiscard]] constexpr bool operator>=(Quantity rhs) const noexcept { return raw_ >= rhs.raw_; }

private:
    int64_t raw_{0};
};

enum class Side : uint8_t { Buy = 0, Sell = 1 };
enum class OrderType : uint8_t { Limit = 0, Market = 1 };
enum class Action : uint8_t { New = 0, Cancel = 1, Modify = 2 };

struct OrderId {
    uint64_t value{0};
    constexpr bool operator==(OrderId rhs) const noexcept { return value == rhs.value; }
    constexpr bool operator!=(OrderId rhs) const noexcept { return value != rhs.value; }
    constexpr bool operator<(OrderId rhs) const noexcept { return value < rhs.value; }
};

struct Order {
    OrderId id{0};
    Side side{Side::Buy};
    OrderType type{OrderType::Limit};
    Price price{};
    Quantity qty{};
    uint64_t timestamp{0};
};

struct Trade {
    OrderId buy_id{0};
    OrderId sell_id{0};
    Price price{};
    Quantity qty{};
    uint64_t timestamp{0};
};

struct OrderAction {
    Action action{Action::New};
    OrderId id{0};
    Side side{Side::Buy};
    OrderType type{OrderType::Limit};
    Price price{};
    Quantity qty{};
};

}  // namespace matching_engine
