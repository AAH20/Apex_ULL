# Implementation status and measurement boundary

The September 2026 repair addresses demonstrated cancellation quantity errors, nontrivial SPSC lifetime, queued-message forwarding, burst bounds, silent DPDK fallback, missing queue publication/reclamation, unsafe hybrid FIFO behavior, synthetic timing metadata, chronological jitter, cost probability units and energy units. Matching and feed components remain research implementations requiring deployment-specific review.

Native tests exercise exact-once payloads with MPMC 4P/4C, MPSC 4P/1C and SPMC 1P/4C at a small ring capacity. This is finite stress coverage; a reserved slot held by a preempted producer can delay progress. No formal lock-free guarantee is claimed.

The Rust real DPDK constructor and affinity requests reject unsupported operation. DPDK/RDMA examples under research reports are distinct from an integrated real transport backend. The RDMA example's throughput conversion uses bits/ns = Gb/s; its local write completion is not remote application round-trip latency. No RDMA hardware was exercised for this change.

The generated native evidence describes software-clock batch measurements. It does not measure wire, NIC, tick-to-trade, exchange execution or individual queue-operation tails. Uncontrolled host conditions and timing overhead are retained as limitations. Atlas checks consistency and declared clock resolution; external uncertainty requires calibrated instrumentation.

FPGA board integration, physical timing, formal properties, production exchange sessions, licensed STAC execution, device-affinity backends and authenticated independent validation remain future work. The earlier README's repository-wide component/test/report totals and production-readiness language were not supported by the public snapshot and are no longer used.
