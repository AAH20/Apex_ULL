#pragma once

#include <version>

#if __cpp_lib_expected >= 202202L
    #include <expected>
#else
    #include <cstddef>
    #include <exception>
    #include <type_traits>
    #include <utility>

namespace std {

template <typename E>
class unexpected {
public:
    constexpr unexpected(const unexpected&) = default;
    constexpr unexpected(unexpected&&) = default;
    constexpr unexpected& operator=(const unexpected&) = default;
    constexpr unexpected& operator=(unexpected&&) = default;

    template <typename Err = E>
        requires(!is_same_v<remove_cvref_t<Err>, unexpected>)
    constexpr explicit unexpected(Err&& e) : e_(forward<Err>(e)) {}

    constexpr const E& error() const& noexcept { return e_; }
    constexpr E& error() & noexcept { return e_; }
    constexpr const E&& error() const&& noexcept { return move(e_); }
    constexpr E&& error() && noexcept { return move(e_); }

private:
    E e_;
};

template <typename E>
unexpected(E) -> unexpected<E>;

template <typename T, typename E>
class expected {
public:
    using value_type = T;
    using error_type = E;

    template <typename U = T>
        requires is_constructible_v<T, U>
    constexpr expected(U&& v) : has_val_(true), val_(forward<U>(v)) {}

    template <typename G = E>
        requires is_constructible_v<E, G>
    constexpr expected(unexpected<G>&& u) : has_val_(false), err_(forward<G>(u.error())) {}

    constexpr expected(const expected&) = default;
    constexpr expected(expected&&) = default;
    constexpr expected& operator=(const expected&) = default;
    constexpr expected& operator=(expected&&) = default;
    constexpr ~expected() = default;

    constexpr bool has_value() const noexcept { return has_val_; }
    constexpr explicit operator bool() const noexcept { return has_val_; }

    constexpr T& value() & {
        if (!has_val_) terminate();
        return val_;
    }
    constexpr const T& value() const& {
        if (!has_val_) terminate();
        return val_;
    }
    constexpr T&& value() && {
        if (!has_val_) terminate();
        return move(val_);
    }

    constexpr E& error() & {
        if (has_val_) terminate();
        return err_;
    }
    constexpr const E& error() const& {
        if (has_val_) terminate();
        return err_;
    }

    constexpr T& operator*() & { return val_; }
    constexpr const T& operator*() const& { return val_; }
    constexpr T* operator->() { return &val_; }
    constexpr const T* operator->() const { return &val_; }

private:
    bool has_val_;
    union {
        T val_;
        E err_;
    };
};

template <typename E>
class expected<void, E> {
public:
    using value_type = void;
    using error_type = E;

    constexpr expected() : has_val_(true) {}

    template <typename G = E>
        requires is_constructible_v<E, G>
    constexpr expected(unexpected<G>&& u) : has_val_(false), err_(forward<G>(u.error())) {}

    constexpr expected(const expected&) = default;
    constexpr expected(expected&&) = default;
    constexpr expected& operator=(const expected&) = default;
    constexpr expected& operator=(expected&&) = default;
    constexpr ~expected() = default;

    constexpr bool has_value() const noexcept { return has_val_; }
    constexpr explicit operator bool() const noexcept { return has_val_; }

    constexpr void value() const {
        if (!has_val_) terminate();
    }

    constexpr E& error() & {
        if (has_val_) terminate();
        return err_;
    }
    constexpr const E& error() const& {
        if (has_val_) terminate();
        return err_;
    }

    constexpr void operator*() const {}

private:
    bool has_val_;
    E err_;
};

}  // namespace std
#endif
