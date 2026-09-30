# Makefile for RDMA Implementation
# Build: make all
# Test:  make test
# Clean: make clean

CC = gcc
CFLAGS = -O2 -Wall -Wextra
LDFLAGS = -libverbs -lrdmacm -lm

TARGETS = rdma_server rdma_client rdma_benchmark

.PHONY: all test clean

all: $(TARGETS)

rdma_server: rdma_echo_server.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

rdma_client: rdma_echo_client.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

rdma_benchmark: rdma_benchmark.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

test: all
	python3 test_rdma.py --build

clean:
	rm -f $(TARGETS) *.o
