#pragma once

#include <version>
#if defined(__cpp_lib_expected) && __cpp_lib_expected >= 202202L
#include <expected>
namespace net::compat {
using std::expected;
using std::unexpected;
}
#else
#include <exception>
#include <type_traits>
#include <utility>
#include <variant>

// This C++20 subset belongs to the project namespace. Never add types to std:
// libstdc++ still declares the legacy std::unexpected function in C++20.
namespace net::compat {
template <typename E>
class unexpected {
public:
    template <typename Err = E>
        requires (!std::is_same_v<std::remove_cvref_t<Err>, unexpected>)
    constexpr explicit unexpected(Err&& error) : error_(std::forward<Err>(error)) {}
    constexpr E& error() & noexcept { return error_; }
    constexpr const E& error() const& noexcept { return error_; }
    constexpr E&& error() && noexcept { return std::move(error_); }
private:
    E error_;
};
template <typename E> unexpected(E) -> unexpected<E>;

template <typename T, typename E>
class expected {
public:
    using value_type = T;
    using error_type = E;
    template <typename U = T>
        requires (std::is_constructible_v<T,U> && !std::is_same_v<std::remove_cvref_t<U>,expected>)
    constexpr expected(U&& value) : storage_(std::in_place_index<0>,std::forward<U>(value)) {}
    template <typename G>
        requires std::is_constructible_v<E,G>
    constexpr expected(unexpected<G>&& error) : storage_(std::in_place_index<1>,std::move(error).error()) {}
    constexpr bool has_value() const noexcept { return storage_.index()==0; }
    constexpr explicit operator bool() const noexcept { return has_value(); }
    constexpr T& value() & { if (!has_value()) std::terminate(); return std::get<0>(storage_); }
    constexpr const T& value() const& { if (!has_value()) std::terminate(); return std::get<0>(storage_); }
    constexpr T&& value() && { if (!has_value()) std::terminate(); return std::get<0>(std::move(storage_)); }
    constexpr E& error() & { if (has_value()) std::terminate(); return std::get<1>(storage_); }
    constexpr const E& error() const& { if (has_value()) std::terminate(); return std::get<1>(storage_); }
    constexpr T& operator*() & { return value(); }
    constexpr const T& operator*() const& { return value(); }
    constexpr T* operator->() { return &value(); }
    constexpr const T* operator->() const { return &value(); }
private:
    std::variant<T,E> storage_;
};

template <typename E>
class expected<void,E> {
public:
    using value_type = void;
    using error_type = E;
    constexpr expected() : storage_(std::in_place_index<0>) {}
    template <typename G>
        requires std::is_constructible_v<E,G>
    constexpr expected(unexpected<G>&& error) : storage_(std::in_place_index<1>,std::move(error).error()) {}
    constexpr bool has_value() const noexcept { return storage_.index()==0; }
    constexpr explicit operator bool() const noexcept { return has_value(); }
    constexpr void value() const { if (!has_value()) std::terminate(); }
    constexpr void operator*() const { value(); }
    constexpr E& error() & { if (has_value()) std::terminate(); return std::get<1>(storage_); }
    constexpr const E& error() const& { if (has_value()) std::terminate(); return std::get<1>(storage_); }
private:
    std::variant<std::monostate,E> storage_;
};
} // namespace net::compat
#endif
