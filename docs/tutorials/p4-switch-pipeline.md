# Tutorial: P4 Switch Pipeline

**Domain:** Network  
**Difficulty:** Advanced  
**Duration:** 3–4 hours

---

## Overview

In this tutorial, you'll write a P4 program that implements a simple forwarding pipeline for a programmable switch. The program will parse Ethernet/IP headers, make forwarding decisions, and modify packet headers.

## What You'll Build

- A P4 program with parser, match-action tables, and deparser
- A P4Runtime controller to install flow rules
- A test environment using Mininet or hardware

## Prerequisites

- P4 compiler (p4c) installed
- Bmv2 software switch (for testing) or Tofino hardware
- Python 3 with p4runtime library
- Basic understanding of packet headers

---

## Step 1: Define the P4 Program

```p4
// simple_forwarder.p4
#include <core.p4>
#include <v1model.p4>

// Header definitions
header ethernet_t {
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}

header ipv4_t {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
}

// Metadata
struct metadata {
    bit<9> egress_port;
}

// Parser
parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            0x0800: parse_ipv4;
            default: accept;
        }
    }
    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition accept;
    }
}

// Ingress pipeline
control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    
    action drop() {
        mark_to_drop(standard_metadata);
    }
    
    action forward(bit<9> port) {
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }
    
    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            forward;
            drop;
            NoAction;
        }
        size = 1024;
        default_action = drop();
    }
    
    apply {
        if (hdr.ipv4.isValid()) {
            ipv4_lpm.apply();
        }
    }
}

// Egress pipeline
control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    
    action rewrite_mac(bit<48> new_dst) {
        hdr.ethernet.dstAddr = new_dst;
    }
    
    table mac_rewrite {
        key = {
            standard_metadata.egress_port: exact;
        }
        actions = {
            rewrite_mac;
            NoAction;
        }
        size = 16;
        default_action = NoAction();
    }
    
    apply {
        mac_rewrite.apply();
    }
}

// Deparser
control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
    }
}

// Checksum verification
control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {
        verify_checksum(hdr.ipv4,
            { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv,
              hdr.ipv4.totalLen, hdr.ipv4.identification,
              hdr.ipv4.flags, hdr.ipv4.fragOffset,
              hdr.ipv4.ttl, hdr.ipv4.protocol,
              hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum, HashAlgorithm.csum16);
    }
}

// Checksum update
control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(hdr.ipv4,
            { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv,
              hdr.ipv4.totalLen, hdr.ipv4.identification,
              hdr.ipv4.flags, hdr.ipv4.fragOffset,
              hdr.ipv4.ttl, hdr.ipv4.protocol,
              hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum, HashAlgorithm.csum16);
    }
}

// Switch definition
V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
```

## Step 2: Compile the P4 Program

```bash
# Compile for Bmv2
p4c --target bmv2 --arch v1model \
    -o simple_forwarder.json \
    simple_forwarder.p4

# Generate P4Info
p4c --target bmv2 --arch v1model \
    --p4info-out simple_forwarder.p4info.txt \
    simple_forwarder.p4
```

## Step 3: P4Runtime Controller (Python)

```python
# controller.py
from p4runtime_lib import helper
from p4runtime_lib import switch
from p4runtime_lib import bmv2

# Switch connection
sw = switch.SwitchConnection(
    name='bmv2-switch',
    address='127.0.0.1:50051',
    device_id=0,
    proto_dump_file='p4runtime.log')

# Load P4Info
p4info_helper = helper.P4InfoHelper('simple_forwarder.p4info.txt')

# Set pipeline config
sw.SetForwardingPipelineConfig(
    p4info=p4info_helper.p4info,
    bmv2_json_file_path='simple_forwarder.json')

# Install forwarding rule
def install_forward_rule(sw, dst_ip, prefix_len, port):
    """Install an LPM rule for IPv4 forwarding."""
    table_entry = p4info_helper.buildTableEntry(
        table_name='MyIngress.ipv4_lpm',
        match_fields={
            'hdr.ipv4.dstAddr': (dst_ip, prefix_len)
        },
        action_name='MyIngress.forward',
        action_params={
            'port': port
        }
    )
    sw.WriteTableEntry(table_entry)
    print(f"Installed rule: {dst_ip}/{prefix_len} -> port {port}")

# Install MAC rewrite rule
def install_mac_rewrite(sw, port, new_dst_mac):
    """Install MAC rewrite rule for egress port."""
    table_entry = p4info_helper.buildTableEntry(
        table_name='MyEgress.mac_rewrite',
        match_fields={
            'standard_metadata.egress_port': port
        },
        action_name='MyEgress.rewrite_mac',
        action_params={
            'new_dst': new_dst_mac
        }
    )
    sw.WriteTableEntry(table_entry)
    print(f"Installed MAC rewrite: port {port} -> {new_dst_mac}")

# Example usage
if __name__ == '__main__':
    # Route 10.0.0.0/24 to port 1
    install_forward_rule(sw, '10.0.0.0', 24, 1)
    
    # Route 10.0.1.0/24 to port 2
    install_forward_rule(sw, '10.0.1.0', 24, 2)
    
    # Rewrite MAC for port 1
    install_mac_rewrite(sw, 1, '00:00:00:00:00:01')
    
    # Read back rules
    print("\nInstalled rules:")
    for entry in sw.ReadTableEntries('MyIngress.ipv4_lpm'):
        print(entry)
```

## Step 4: Test with Bmv2

```bash
# Start Bmv2 with the compiled P4 program
simple_switch --log-console \
    -i 0@veth0 -i 1@veth1 -i 2@veth2 \
    simple_forwarder.json &

# In another terminal, run the controller
python3 controller.py

# Generate test traffic
sudo tcpreplay -i veth0 test_packet.pcap

# Monitor
simple_switch_CLI
# In CLI:
# table_dump MyIngress.ipv4_lpm
# counter_read MyIngress.ipv4_lpm 0
```

## Step 5: Verify

```bash
# Check table entries
simple_switch_CLI << EOF
table_dump MyIngress.ipv4_lpm
counter_read MyIngress.ipv4_lpm 0
EOF

# Expected output shows installed rules and packet counts
```

## Expected Results

| Metric | Value |
|--------|-------|
| Switch latency | 100–500 ns |
| Throughput | 6.5 Tb/s (Tofino) |
| Table lookup | ~10–100 ns |
| Rule capacity | 1024+ entries |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Compilation failed" | Check P4 syntax, verify header definitions |
| "Table full" | Increase table size in P4 program |
| "No packets forwarded" | Verify P4Runtime connection, check table entries |
| "Checksum error" | Verify checksum computation in egress |

## Next Steps

- Add ACL (Access Control List) tables
- Implement traffic metering
- Add INT (In-band Network Telemetry)
- Deploy on Tofino hardware for production performance
