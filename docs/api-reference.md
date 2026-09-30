# Ultra-Low Latency API Reference

**Version:** 1.0  
**Last Updated:** 2026-09-29

---

## Table of Contents

1. [DPDK API](#dpdk-api)
2. [RDMA Verbs API](#rdma-verbs-api)
3. [SPDK API](#spdk-api)
4. [P4 Runtime API](#p4-runtime-api)
5. [Onload API](#onload-api)
6. [DOCA SDK API](#doca-sdk-api)
7. [FPGA Configuration APIs](#fabric-configuration-apis)
8. [Kernel Tuning Interfaces](#kernel-tuning-interfaces)
9. [Measurement APIs](#measurement-apis)

---

## DPDK API

DPDK (Data Plane Development Kit) provides user-space poll-mode drivers for network packet processing.

### Initialization

```c
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_mempool.h>

// Initialize Environment Abstraction Layer
int rte_eal_init(int argc, char *argv[]);

// Get number of available Ethernet ports
uint16_t rte_eth_dev_count_avail(void);

// Configure an Ethernet device
int rte_eth_dev_configure(uint16_t port_id, uint16_t nb_rx_queue,
                          uint16_t nb_tx_queue,
                          const struct rte_eth_conf *eth_conf);
```

### Memory Management

```c
// Create a memory pool (requires hugepages)
struct rte_mempool *rte_pktmbuf_pool_create(const char *name,
    unsigned n, unsigned cache_size, uint16_t priv_size,
    uint16_t data_room_size, int socket_id);

// Allocate mbuf from pool
struct rte_mbuf *rte_pktmbuf_alloc(struct rte_mempool *mp);

// Free mbuf back to pool
void rte_pktmbuf_free(struct rte_mbuf *m);
```

### Packet I/O

```c
// Receive burst of packets
static inline uint16_t rte_eth_rx_burst(uint16_t port_id,
    uint16_t queue_id, struct rte_mbuf **rx_pkts, const uint16_t nb_pkts);

// Transmit burst of packets
static inline uint16_t rte_eth_tx_burst(uint16_t port_id,
    uint16_t queue_id, struct rte_mbuf **tx_pkts, const uint16_t nb_pkts);
```

### Device Configuration

```c
// Set port promiscuous mode
int rte_eth_promiscuous_enable(uint16_t port_id);
int rte_eth_promiscuous_disable(uint16_t port_id);

// Get link status
int rte_eth_link_get(uint16_t port_id, struct rte_eth_link *link);

// Set RX VLAN filter
int rte_eth_dev_set_vlan_filter(uint16_t port_id, uint16_t vlan_id, int on);
```

### Performance Tuning

```c
// Descriptor ring sizes (trade latency vs. throughput)
#define RX_RING_SIZE 1024
#define TX_RING_SIZE 1024

// Burst size (larger = more throughput, higher latency)
#define BURST_SIZE 32

// Number of mbufs in pool (must be power of 2 minus 1)
#define NUM_MBUFS 8191
#define MBUF_CACHE_SIZE 250
```

### DPDK Configuration (dpdk.conf)

```ini
# /etc/dpdk/dpdk.conf
# Hugepage configuration
hugepagesz=1G
hugepages=8

# CPU core isolation
isolcpus=2-7
nohz_full=2-7
rcu_nocbs=2-7

# DPDK EAL options
eal-options=-l 2-7 -n 4 --proc-type=auto
```

---

## RDMA Verbs API

The Verbs API provides direct access to RDMA hardware for zero-copy, kernel-bypass data transfers.

### Device Management

```c
#include <infiniband/verbs.h>

// Get list of RDMA devices
struct ibv_device **ibv_get_device_list(int *num_devices);

// Open device
struct ibv_context *ibv_open_device(struct ibv_device *device);

// Close device
int ibv_close_device(struct ibv_context *ctx);

// Query device capabilities
int ibv_query_device(struct ibv_context *ctx,
                     struct ibv_device_attr *device_attr);

// Query port properties
int ibv_query_port(struct ibv_context *ctx, uint8_t port_num,
                   struct ibv_port_attr *port_attr);
```

### Protection Domain & Memory Registration

```c
// Allocate protection domain
struct ibv_pd *ibv_alloc_pd(struct ibv_context *ctx);

// Register memory region (required for RDMA operations)
struct ibv_mr *ibv_reg_mr(struct ibv_pd *pd, void *addr, size_t length,
                          int access_flags);
// Access flags:
//   IBV_ACCESS_LOCAL_WRITE   - allow local writes
//   IBV_ACCESS_REMOTE_READ  - allow remote reads
//   IBV_ACCESS_REMOTE_WRITE - allow remote writes
//   IBV_ACCESS_REMOTE_ATOMIC - allow atomic operations

// Deregister memory region
int ibv_dereg_mr(struct ibv_mr *mr);
```

### Queue Pair (QP) Management

```c
// Create completion queue
struct ibv_cq *ibv_create_cq(struct ibv_context *ctx, int cqe,
                             void *cq_context, struct ibv_channel *channel,
                             int comp_vector);

// Create queue pair
struct ibv_qp_init_attr qp_init = {
    .send_cq = cq,
    .recv_cq = cq,
    .cap = {
        .max_send_wr = 16,
        .max_recv_wr = 16,
        .max_send_sge = 1,
        .max_recv_sge = 1,
    },
    .qp_type = IBV_QPT_RC,  // Reliable Connection
};
struct ibv_qp *ibv_create_qp(struct ibv_pd *pd,
                             struct ibv_qp_init_attr *qp_init_attr);

// Transition QP to INIT state
struct ibv_qp_attr attr = {
    .qp_state = IBV_QPS_INIT,
    .pkey_index = 0,
    .port_num = 1,
    .qp_access_flags = IBV_ACCESS_REMOTE_READ |
                       IBV_ACCESS_REMOTE_WRITE |
                       IBV_ACCESS_REMOTE_ATOMIC,
};
ibv_modify_qp(qp, &attr,
    IBV_QP_STATE | IBV_QP_PKEY_INDEX | IBV_QP_PORT | IBV_QP_ACCESS_FLAGS);

// Transition QP to RTR (Ready To Receive)
// ... (requires peer QP info: LID, QPN, GID)

// Transition QP to RTS (Ready To Send)
// ... (requires local and peer QPN)
```

### RDMA Operations

```c
// Post RDMA READ (remote memory → local memory)
struct ibv_sge sge = {
    .addr = (uintptr_t)local_buf,
    .length = 4096,
    .lkey = mr->lkey,
};
struct ibv_send_wr rdma_wr = {
    .wr_id = 1,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_RDMA_READ,
    .send_flags = IBV_SEND_SIGNALED,
    .wr.rdma = {
        .remote_addr = remote_addr,
        .rkey = remote_rkey,
    },
};
struct ibv_send_wr *bad_wr;
ibv_post_send(qp, &rdma_wr, &bad_wr);

// Post RDMA WRITE (local memory → remote memory)
rdma_wr.opcode = IBV_WR_RDMA_WRITE;

// Post SEND/RECV (message passing)
rdma_wr.opcode = IBV_WR_SEND;

// Post atomic compare-and-swap
rdma_wr.opcode = IBV_WR_ATOMIC_CMP_AND_SWP;
rdma_wr.wr.atomic = {
    .remote_addr = remote_addr,
    .compare_add = expected_value,
    .swap = new_value,
    .rkey = remote_rkey,
};
```

### Completion Handling

```c
// Poll completion queue
struct ibv_wc wc;
int ne = ibv_poll_cq(cq, 1, &wc);

if (ne > 0 && wc.status == IBV_WC_SUCCESS) {
    // Operation completed successfully
    uint64_t wr_id = wc.wr_id;
    // Process completion...
}
```

---

## SPDK API

SPDK (Storage Performance Development Kit) provides user-space, poll-mode drivers for NVMe and NVMe-oF.

### Initialization

```c
#include <spdk/env.h>
#include <spdk/nvme.h>

// Initialize SPDK environment
struct spdk_env_opts opts;
spdk_env_opts_init(&opts);
opts.name = "my_app";
opts.core_mask = "0x3";  // Use cores 0-1
spdk_env_init(&opts);

// Probe NVMe controllers
spdk_nvme_probe(NULL, NULL, probe_cb, attach_cb, NULL);
```

### NVMe I/O

```c
// Read from NVMe device
int spdk_nvme_ns_cmd_read(struct spdk_nvme_ns *ns,
                          struct spdk_nvme_qpair *qpair,
                          void *payload, uint64_t lba,
                          uint32_t lba_count,
                          spdk_nvme_cmd_completion_cb cb,
                          void *cb_arg, uint32_t io_flags);

// Write to NVMe device
int spdk_nvme_ns_cmd_write(struct spdk_nvme_ns *ns,
                           struct spdk_nvme_qpair *qpair,
                           void *payload, uint64_t lba,
                           uint32_t lba_count,
                           spdk_nvme_cmd_completion_cb cb,
                           void *cb_arg, uint32_t io_flags);

// Submit and wait for completion
spdk_nvme_qpair_process_completions(qpair, max_completions);
```

### NVMe-oF Target

```c
// Create NVMe-oF target subsystem
struct spdk_nvmf_subsystem *subsys = spdk_nvmf_subsystem_create(
    NVMF_NQN.2014-08.org.nvmdiscovery, "SPDK NVMe-oF Target");

// Add namespace (NVMe SSD)
spdk_nvmf_subsystem_add_ns(subsys, &ns_opts);

// Add listener (RDMA transport)
struct spdk_nvme_transport_id trid = {
    .trtype = SPDK_NVME_TRANSPORT_RDMA,
    .adrfam = SPDK_NVMF_ADRFAM_IPV4,
    .traddr = "192.168.1.100",
    .trsvcid = "4420",
};
spdk_nvmf_subsystem_add_listener(subsys, &trid);
```

---

## P4 Runtime API

P4 Runtime (P4Runtime) provides control-plane interfaces for P4-programmable switches.

### P4Info Configuration

```protobuf
// p4info.txt — describes the P4 program's interfaces
tables {
  preamble { id: 1 name: "forwarding_table" }
  match_fields {
    id: 1 name: "hdr.ipv4.dstAddr"
    bitwidth: 32 match_type: LPM
  }
  action_refs { id: 1 name: "forward" }
  action_refs { id: 2 name: "drop" }
  size: 1024
}
```

### P4Runtime Service (gRPC)

```protobuf
service P4Runtime {
  rpc Write(WriteRequest) returns (WriteResponse);
  rpc Read(ReadRequest) returns (stream ReadResponse);
  rpc SetForwardingPipelineConfig(SetForwardingPipelineConfigRequest)
      returns (SetForwardingPipelineConfigResponse);
  rpc GetForwardingPipelineConfig(GetForwardingPipelineConfigRequest)
      returns (GetForwardingPipelineConfigResponse);
  rpc StreamChannel(stream StreamMessageRequest)
      returns (stream StreamMessageResponse);
}
```

### Table Entry Programming

```python
from p4runtime_lib import helper
from p4runtime_lib import switch

# Connect to P4 switch
sw = switch.SwitchConnection(
    name='tofino-switch',
    address='10.0.0.1:50051',
    device_id=0,
    proto_dump_file='p4runtime.log')

# Build table entry
p4info_helper = helper.P4InfoHelper('p4info.txt')
table_entry = p4info_helper.buildTableEntry(
    table_name='forwarding_table',
    match_fields={'hdr.ipv4.dstAddr': ('10.0.0.0', 24)},
    action_name='forward',
    action_params={'port': 1})

# Install entry
sw.WriteTableEntry(table_entry)

# Monitor packets
sw.StreamMessageUpdate()
```

---

## Onload API

Onload provides kernel-bypass networking with a standard socket API (Solarflare/AMD NICs).

### Basic Usage

```c
#include <onload/extensions.h>

// Onload automatically intercepts socket calls
// No code changes needed for basic usage

// Explicit stack creation
int fd = onload_socket(AF_INET, SOCK_STREAM, 0);

// Set per-socket options
onload_set_stackname(fd, ONLOAD_SCOPE_THREAD, "my_stack");

// Move socket to specific stack
onload_fd_set_stackname(fd, "my_stack");
```

### Advanced: ef_vi (Direct API)

```c
#include <etherfabric/vi.h>

// Initialize ef_vi
struct ef_vi vi;
ef_vi_init(&vi, ef_driver_handle, ifindex, EF_VI_FLAGS_DEFAULT);

// Allocate RX ring
ef_vi_rx_ring_alloc(&vi, &rx_ring, num_rx_descs);

// Post RX buffer
ef_vi_rx_post(&vi, &rx_ring, rx_buf, rx_buf_id);

// Poll for received packets
int n_rx = ef_vi_rx_poll(&vi, &rx_ring);

// Transmit packet
ef_vi_tx_alloc(&vi, &tx_desc, pkt_len);
ef_vi_tx_send(&vi, &tx_desc);
```

---

## DOCA SDK API

DOCA (Data Center Infrastructure on a Chip Architecture) is NVIDIA's SDK for BlueField DPU programming.

### DOCA Core

```c
#include <doca_dev.h>
#include <doca_buf.h>
#include <doca_buf_inventory.h>

// Open DOCA device
struct doca_dev *dev;
doca_dev_open(&dev, &devinfo);

// Create buffer inventory
struct doca_buf_inventory *inventory;
doca_buf_inventory_create(&inventory, num_buffers, NULL);
doca_buf_inventory_start(inventory);

// Allocate buffer
struct doca_buf *buf;
doca_buf_inventory_buf_get_by_addr(inventory, mmap, addr, len, &buf);

// Get buffer data pointer
uint8_t *data;
doca_buf_get_data(buf, (void **)&data, &data_len);
```

### DOCA Flow (Packet Processing)

```c
// Create flow pipe
struct doca_flow_pipe *pipe;
doca_flow_pipe_create(&pipe_cfg, &pipe);

// Add entry to pipe
struct doca_flow_match match = {
    .outer = { .l3_type = DOCA_FLOW_L3_TYPE_IP4,
               .ip4.dst_ip = 0x0A000001 },
};
struct doca_flow_actions actions = {
    .dec_hlim = 1,
    .has_encap = 1,
};
struct doca_flow_fwd fwd = { .type = DOCA_FLOW_FWD_RSS };
doca_flow_pipe_add_entry(0, pipe, &match, &actions, &fwd, NULL, &entry);
```

---

## FPGA Configuration APIs

### Xilinx XRT (Xilinx Runtime)

```c
#include <xrt/xrt.h>

// Load bitstream onto FPGA
xclDeviceHandle handle = xclOpen(device_index, NULL, XCL_INFO);
xclLoadXclBin(handle, (const xclBin *)bitstream_buffer);

// Allocate device memory
xclBufferHandle buf = xclAllocBO(handle, size, 0, XCL_BO_FLAGS_DEV_MEM);

// Map to host address
void *host_ptr = xclMapBO(handle, buf, true);

// Start kernel
xclSyncBO(handle, buf, XCL_BO_SYNC_BO_TO_DEVICE, size, 0);
xclExecBuf(handle, exec_buf);
```

### Intel OpenCL

```c
// Load FPGA binary
cl_context context = clCreateContextFromType(CL_DEVICE_TYPE_ACCELERATOR);
cl_program program = clCreateProgramWithBinary(context, 1, &device,
    &binary_size, (const unsigned char **)&binary, NULL, &err);
clBuildProgram(program, 1, &device, "", NULL, NULL);

// Create kernel
cl_kernel kernel = clCreateKernel(program, "my_kernel", &err);

// Set kernel arguments
clSetKernelArg(kernel, 0, sizeof(cl_mem), &input_buf);
clSetKernelArg(kernel, 1, sizeof(cl_mem), &output_buf);

// Execute kernel
clEnqueueNDRangeKernel(queue, kernel, 1, NULL, &global_size,
    &local_size, 0, NULL, NULL);
```

---

## Kernel Tuning Interfaces

### sysctl Parameters

```bash
# /etc/sysctl.conf for ULL systems

# Hugepages
vm.nr_hugepages = 8
vm.hugetlb_shm_group = 200

# Network
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.netdev_max_backlog = 300000
net.core.somaxconn = 65535
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_notsent_lowat = 16384

# Kernel
kernel.numa_balancing = 0
kernel.watchdog = 0
kernel.hung_task_timeout_secs = 0
kernel.sched_rt_runtime_us = -1
```

### CPU Isolation

```bash
# /etc/default/grub
GRUB_CMDLINE_LINUX="isolcpus=2-7 nohz_full=2-7 rcu_nocbs=2-7 \
    intel_pstate=disable processor.max_cstate=1 \
    idle=poll default_hugepagesz=1G hugepagesz=1G hugepages=8"

# Apply
update-grub
reboot
```

### IRQ Affinity

```bash
# Pin NIC interrupts to specific cores
# /proc/irq/<IRQ>/smp_affinity
echo 4 > /proc/irq/42/smp_affinity  # Core 2 only

# Or use irqbalance with manual hints
IRQBALANCE_BANNED_CPULIST=2-7
IRQBALANCE_ARGS="--policyscript=/usr/local/bin/irqpolicy.sh"
```

---

## Measurement APIs

### High-Resolution Timing

```c
// x86 RDTSC (Time Stamp Counter)
static inline uint64_t rdtsc(void) {
    unsigned int lo, hi;
    __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

// RDTSCP (serialized, prevents reordering)
static inline uint64_t rdtscp(void) {
    unsigned int aux;
    return __rdtscp(&aux);
}

// ARM PMCCNTR (Performance Monitors Cycle Count Register)
static inline uint64_t arm_cycle_count(void) {
    uint64_t val;
    __asm__ __volatile__("mrs %0, pmccntr_el0" : "=r"(val));
    return val;
}
```

### Linux perf_event

```c
#include <linux/perf_event.h>
#include <sys/syscall.h>

// Open perf event
struct perf_event_attr pe = {
    .type = PERF_TYPE_HARDWARE,
    .size = sizeof(struct perf_event_attr),
    .config = PERF_COUNT_HW_CPU_CYCLES,
    .disabled = 1,
    .exclude_kernel = 1,
    .exclude_hv = 1,
};
int fd = syscall(__NR_perf_event_open, &pe, 0, -1, -1, 0);

// Enable and read
ioctl(fd, PERF_EVENT_IOC_RESET, 0);
ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
// ... code to measure ...
ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
uint64_t count;
read(fd, &count, sizeof(count));
```

### DPDK Timestamps

```c
// Enable hardware timestamping
struct rte_eth_timesync_info timesync = {
    .rx_filter = RTE_ETH_RX_OFFLOAD_TIMESTAMP,
    .tx_type = RTE_ETH_TX_OFFLOAD_SEND_ON_TIMESTAMP,
};
rte_eth_timesync_enable(port_id);

// Read timestamp from mbuf
uint64_t timestamp = rte_mbuf_timestamp_get(m);
```

---

## Configuration File Reference

### DPDK EAL Options

| Option | Description | Example |
|--------|-------------|---------|
| `-l` | Core list | `-l 2-7` |
| `-n` | Memory channels | `-n 4` |
| `--proc-type` | Process type | `--proc-type=auto` |
| `--huge-dir` | Hugepage mount point | `--huge-dir=/mnt/huge` |
| `--socket-mem` | Memory per socket | `--socket-mem=1024,1024` |
| `--pci-whitelist` | Allow PCI devices | `--pci-whitelist=0000:03:00.0` |

### RDMA Configuration

```bash
# /etc/rdma/rdma.conf
# Enable RoCE v2
ROCE_ENABLE=yes
ROCE_VERSION=2

# Buffer sizes
ROCE_SQ_SIZE=128
ROCE_RQ_SIZE=128
ROCE_CQ_SIZE=256

# PFC (Priority Flow Control) for lossless Ethernet
PFC_ENABLE=yes
PFC_PRIORITY=3
```

### Kernel Boot Parameters for ULL

```bash
# Minimal latency kernel parameters
isolcpus=2-7              # Isolate cores 2-7 from scheduler
nohz_full=2-7             # No tick on isolated cores
rcu_nocbs=2-7             # Offload RCU callbacks
intel_pstate=disable      # Disable CPU frequency scaling
processor.max_cstate=1     # Limit C-state depth
idle=poll                 # Poll instead of idle
default_hugepagesz=1G     # 1GB hugepages
hugepagesz=1G
hugepages=8               # 8 x 1GB hugepages
```

---

## Error Codes

### DPDK Error Codes

| Code | Name | Description |
|------|------|-------------|
| -1 | RTE_EAL_ERR | EAL initialization failed |
| -2 | RTE_ETH_ERR | Ethernet device error |
| -3 | RTE_MBUF_ERR | Memory buffer error |
| -4 | RTE_MEMPOOL_ERR | Memory pool error |

### RDMA Error Codes

| Code | Name | Description |
|------|------|-------------|
| EINVAL | Invalid argument | Bad parameter |
| ENOMEM | Out of memory | Registration failed |
| ECONNREFUSED | Connection refused | Peer not available |
| ETIMEDOUT | Timeout | Operation timed out |
| EREMOTE | Remote error | Remote side error |

---

## Further Reading

- [Architecture Guide](architecture.md) — System design patterns
- [Tutorials](tutorials/) — Hands-on implementation guides
- [Network Technologies Report](../reports/network-technologies.md) — RDMA, DPU, P4 details
- [FPGA Technologies Report](../reports/fpga-technologies.md) — FPGA selection and configuration
