cmake_minimum_required(VERSION 3.20)
project(udp_network LANGUAGES CXX VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(UDP_NETWORK_BUILD_TESTS "Build unit tests" ON)
option(UDP_NETWORK_BUILD_BENCHMARKS "Build benchmarks" ON)

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

add_library(udp_network
    src/udp_socket.cpp
    src/zero_copy_buffer.cpp
    src/udp_sender.cpp
)

target_include_directories(udp_network
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(udp_network PUBLIC cxx_std_20)

find_package(Threads REQUIRED)
target_link_libraries(udp_network PUBLIC Threads::Threads)

if(UDP_NETWORK_BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    add_executable(udp_network_tests
        tests/test_udp_socket.cpp
        tests/test_zero_copy_buffer.cpp
        tests/test_udp_sender.cpp
    )
    target_link_libraries(udp_network_tests PRIVATE udp_network GTest::gtest_main)
    add_test(NAME udp_network_tests COMMAND udp_network_tests)
endif()

if(UDP_NETWORK_BUILD_BENCHMARKS)
    find_package(benchmark REQUIRED)
    add_executable(udp_network_benchmarks
        benchmarks/bench_udp_socket.cpp
        benchmarks/bench_zero_copy_buffer.cpp
        benchmarks/bench_udp_sender.cpp
    )
    target_link_libraries(udp_network_benchmarks PRIVATE udp_network benchmark::benchmark_main)
endif()
