cmake_minimum_required(VERSION 3.20)
project(tcp_network LANGUAGES CXX VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(TCP_NETWORK_BUILD_TESTS "Build unit tests" ON)
option(TCP_NETWORK_BUILD_BENCHMARKS "Build benchmarks" ON)

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

add_library(tcp_network
    src/socket.cpp
    src/buffer.cpp
    src/event_loop.cpp
    src/tcp_server.cpp
    src/tcp_client.cpp
)

target_include_directories(tcp_network
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(tcp_network PUBLIC cxx_std_20)

find_package(Threads REQUIRED)
target_link_libraries(tcp_network PUBLIC Threads::Threads)

if(TCP_NETWORK_BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    add_executable(tcp_network_tests
        tests/test_socket.cpp
        tests/test_buffer.cpp
        tests/test_event_loop.cpp
        tests/test_tcp_server.cpp
        tests/test_tcp_client.cpp
    )
    target_link_libraries(tcp_network_tests PRIVATE tcp_network GTest::gtest_main)
    add_test(NAME tcp_network_tests COMMAND tcp_network_tests)
endif()

if(TCP_NETWORK_BUILD_BENCHMARKS)
    find_package(benchmark REQUIRED)
    add_executable(tcp_network_benchmarks
        benchmarks/bench_socket.cpp
        benchmarks/bench_buffer.cpp
        benchmarks/bench_event_loop.cpp
        benchmarks/bench_tcp_server.cpp
    )
    target_link_libraries(tcp_network_benchmarks PRIVATE tcp_network benchmark::benchmark_main)
endif()
