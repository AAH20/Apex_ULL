# ULL Network Stack

Ultra-low-latency network stack with kernel bypass, zero-copy, and lock-free data paths.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Application Layer                                  │
│  • HFT strategy, market data handler                │
├─────────────────────────────────────────────────────┤
│  NetStack (top-level)                               │
│  • Multi-port management                            │
│  • Global statistics                                │
├─────────────────────────────────────────────────────┤
│  NetPort (per-NIC)                                  │
│  • Buffer pool (hugepage-backed)                    │
│  • Queue pair management                            │
│  • RX/TX burst processing                           │
├─────────────────────────────────────────────────────┤
│  NetQP (per-connection)                             │
│  • TX/RX rings (SPSC, lock-free)                    │
│  • Completion queues (TX/RX)                        │
│  • Connection state machine                         │
├─────────────────────────────────────────────────────┤
│  NetRing / NetCQ (lock-free primitives)             │
│  • SPSC ring: no CAS on fast path                   │
│  • Cache-line aligned, false-sharing prevention     │
│  • Batch operations for amortized overhead          │
├─────────────────────────────────────────────────────┤
│  NetBufPool (zero-copy)                             │
│  • Hugepage-backed contiguous memory                │
│  • LIFO free stack (lock-free)                      │
│  • Buffer descriptors only move through rings       │
└─────────────────────────────────────────────────────┘
```

## Key Design Principles

### Zero-Copy
Packet buffers are allocated once from hugepage-backed pools and never copied. Only descriptors (pointers) move through rings. This eliminates:
- Kernel-user space copies
- Memory allocation on the hot path
- Cache pollution from data movement

### Lock-Free
All rings use SPSC (Single Producer, Single Consumer) topology with:
- Relaxed atomics on the fast path (no CAS)
- Release/acquire semantics for ordering
- Cache-line alignment to prevent false sharing

### Poll-Mode
No interrupts. Pure polling for deterministic latency:
- No context switches on the data path
- No interrupt handler overhead
- Predictable latency distribution

### Batch Operations
Amortize atomic overhead across multiple packets:
- `net_ring_push_batch()` / `net_ring_pop_batch()`
- Reduces per-packet atomic operations by 32x

## Components

### NetBufPool
Zero-copy packet buffer pool backed by hugepage memory.

```python
pool = NetBufPool(capacity=65536, buf_size=9000)
buf_idx = pool.alloc()  # O(1), lock-free
pool.free(buf_idx)      # O(1), lock-free
```

### NetRing
SPSC lock-free ring buffer for packet descriptors.

```python
ring = NetRing(capacity=4096)
ring.push(buf_ptr)      # No CAS on fast path
buf_ptr = ring.pop()    # No CAS on fast path
```

### NetCQ
Lock-free completion queue for TX/RX completions.

```python
cq = NetCQ(capacity=4096)
cq.push(buf_ptr, status, length, timestamp_ns)
cqe = cq.pop()
```

### NetQP
RDMA-style Queue Pair for connection management.

```python
qp = NetQP(qp_num=1, pool=pool, ring_size=4096)
qp.send(buf_ptr)
buf_ptr = qp.recv()
```

### NetPort
NIC port abstraction with buffer pool and queue pairs.

```python
port = NetPort(port_id=0, name="eth0")
qp = port.create_qp(qp_num=1)
```

### NetStack
Top-level network stack managing multiple ports.

```python
stack = NetStack(num_ports=2)
port = stack.get_port(0)
```

## Building

### C Library
```bash
cd applications/network-stack
clang -O3 -march=native -shared -fPIC -o libnetstack.so net_stack.c
```

### C Benchmark
```bash
clang -O3 -march=native -o net_stack_bench net_stack_bench.c net_stack.c
./net_stack_bench [iterations]
```

### Python
```bash
# The Python module auto-builds the C library on first import
python3 -c "from applications.network_stack import NetStack; print('OK')"
```

## Benchmarking

### Python Benchmark
```bash
python3 -m applications.network_stack.benchmark --quick
python3 -m applications.network_stack.benchmark --output results.json
```

### C Benchmark
```bash
./net_stack_bench 1000000
```

## Performance Targets

| Component | Latency (p50) | Latency (p99) | Throughput |
|-----------|---------------|---------------|------------|
| Ring push/pop | ~10 ns | ~50 ns | >100M ops/s |
| Buffer alloc/free | ~15 ns | ~80 ns | >50M ops/s |
| CQ push/pop | ~12 ns | ~60 ns | >80M ops/s |
| QP send/recv | ~25 ns | ~120 ns | >30M ops/s |

## Comparison with Standard Stack

| Metric | Standard Kernel | ULL Network Stack |
|--------|-----------------|-------------------|
| Latency | 10-50 μs | 1-5 μs |
| Jitter | High | Low |
| Throughput | 1-10 Mpps | 100+ Mpps |
| CPU overhead | High (syscalls) | Low (poll-mode) |
| Determinism | No | Yes |

## References

- DPDK: https://doc.dpdk.org/
- RDMA: https://www.openfabrics.org/
- LMAX Disruptor: https://lmax-exchange.github.io/disruptor/
- Solarflare Onload: https://www.solarflare.com/
