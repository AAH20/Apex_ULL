cmake_minimum_required(VERSION 3.20)
project(matching_engine LANGUAGES CXX VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(MATCHING_ENGINE_BUILD_TESTS "Build unit tests" ON)
option(MATCHING_ENGINE_BUILD_BENCHMARKS "Build benchmarks" ON)

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

add_library(matching_engine
    src/order_book.cpp
    src/matching_engine.cpp
)

target_include_directories(matching_engine
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(matching_engine PUBLIC cxx_std_20)

find_package(Threads REQUIRED)
target_link_libraries(matching_engine PUBLIC Threads::Threads)

if(MATCHING_ENGINE_BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    add_executable(matching_engine_tests
        tests/test_types.cpp
        tests/test_order_book.cpp
        tests/test_matching_engine.cpp
        tests/test_spsc_queue.cpp
    )
    target_link_libraries(matching_engine_tests PRIVATE matching_engine GTest::gtest_main)
    add_test(NAME matching_engine_tests COMMAND matching_engine_tests)
endif()

if(MATCHING_ENGINE_BUILD_BENCHMARKS)
    find_package(benchmark REQUIRED)
    add_executable(matching_engine_benchmarks
        benchmarks/bench_matching_engine.cpp
        benchmarks/bench_order_book.cpp
        benchmarks/bench_spsc_queue.cpp
    )
    target_link_libraries(matching_engine_benchmarks PRIVATE matching_engine benchmark::benchmark_main)
endif()
