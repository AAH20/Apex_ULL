// simple_forwarder.p4 — P4 Program for ULL Network
//
// Implements:
// - Ethernet/IPv4 parsing
// - LPM forwarding table
// - MAC rewrite on egress
// - TTL decrement
// - Checksum verification/update
// - Drop action for unmatched packets
//
// Compile: p4c --target bmv2 --arch v1model -o simple_forwarder.json simple_forwarder.p4

#include <core.p4>
#include <v1model.p4>

// ── Header Definitions ──

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

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> length;
    bit<16> checksum;
}

// ── Metadata ──

struct metadata {
    bit<9>  egress_port;
    bit<32> hash;
}

struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;
    udp_t      udp;
}

// ── Parser ──

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
        transition select(hdr.ipv4.protocol) {
            17: parse_udp;
            default: accept;
        }
    }
    state parse_udp {
        packet.extract(hdr.udp);
        transition accept;
    }
}

// ── Ingress Pipeline ──

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

    action compute_hash() {
        meta.hash = hash(HashAlgorithm.crc16,
            { hdr.ipv4.srcAddr, hdr.ipv4.dstAddr,
              hdr.udp.srcPort, hdr.udp.dstPort,
              hdr.ipv4.protocol });
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

    table udp_forward {
        key = {
            hdr.udp.dstPort: exact;
        }
        actions = {
            forward;
            drop;
            NoAction;
        }
        size = 256;
        default_action = drop();
    }

    apply {
        if (hdr.ipv4.isValid()) {
            ipv4_lpm.apply();
            if (hdr.udp.isValid()) {
                udp_forward.apply();
            }
        }
    }
}

// ── Egress Pipeline ──

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    action rewrite_mac(bit<48> new_dst) {
        hdr.ethernet.dstAddr = new_dst;
    }

    action rewrite_src_mac(bit<48> new_src) {
        hdr.ethernet.srcAddr = new_src;
    }

    table mac_rewrite {
        key = {
            standard_metadata.egress_port: exact;
        }
        actions = {
            rewrite_mac;
            rewrite_src_mac;
            NoAction;
        }
        size = 16;
        default_action = NoAction();
    }

    apply {
        mac_rewrite.apply();
    }
}

// ── Deparser ──

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.udp);
    }
}

// ── Checksum Verification ──

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

// ── Checksum Update ──

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

// ── Switch Definition ──

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
