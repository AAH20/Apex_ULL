cmake_minimum_required(VERSION 3.20)
project(feed_handler LANGUAGES CXX VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Options ───────────────────────────────────────────────────────────────────
option(FEED_HANDLER_BUILD_TESTS "Build unit tests" ON)
option(FEED_HANDLER_BUILD_BENCHMARKS "Build benchmarks" ON)

# ── Compiler flags ────────────────────────────────────────────────────────────
add_compile_options(
    -Wall -Wextra -Wpedantic
    -Wshadow -Wnon-virtual-dtor -Wold-style-cast
    -Wcast-align -Wunused -Woverloaded-virtual
    -Wconversion -Wsign-conversion
    -Wnull-dereference -Wdouble-promotion
    -Wformat=2
)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-march=native -O3)
endif()

# ── Library ───────────────────────────────────────────────────────────────────
add_library(feed_handler
    src/dpdk_bypass.cpp
    src/feed_handler.cpp
)

target_include_directories(feed_handler
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(feed_handler PUBLIC cxx_std_20)

# ── Dependencies ──────────────────────────────────────────────────────────────
find_package(Threads REQUIRED)
target_link_libraries(feed_handler PUBLIC Threads::Threads)

# ── Tests ─────────────────────────────────────────────────────────────────────
if(FEED_HANDLER_BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    add_executable(feed_handler_tests
        tests/test_cache_line.cpp
        tests/test_spsc_ring.cpp
        tests/test_parser.cpp
        tests/test_feed_handler.cpp
    )
    target_link_libraries(feed_handler_tests PRIVATE feed_handler GTest::gtest_main)
    add_test(NAME feed_handler_tests COMMAND feed_handler_tests)
endif()

# ── Benchmarks ────────────────────────────────────────────────────────────────
if(FEED_HANDLER_BUILD_BENCHMARKS)
    find_package(benchmark REQUIRED)
    add_executable(feed_handler_benchmarks
        benchmarks/bench_spsc_ring.cpp
        benchmarks/bench_parser.cpp
        benchmarks/bench_feed_handler.cpp
    )
    target_link_libraries(feed_handler_benchmarks PRIVATE feed_handler benchmark::benchmark_main)
endif()
