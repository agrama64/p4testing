/* P4 NAT implementation with simple forwarding */
#include <core.p4>
#include <v1model.p4>

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

struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;
}

struct metadata { }

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
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

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action drop() {
        mark_to_drop(standard_metadata);
    }

    // *** NAT ACTIONS ***

    // NAT translation action for outbound traffic
    // Removed unused public_port parameter
    action nat_translate_outbound(bit<32> public_ip) {
        // Store original IP/port in metadata for reverse translation if needed

        // Modify source IP to public IP
        hdr.ipv4.srcAddr = public_ip;

        // Update checksum (will be recomputed later)
        hdr.ipv4.hdrChecksum = 0;

        // *** FORWARDING LOGIC ADDED HERE ***
        // Forward outbound traffic to external network interface
        standard_metadata.egress_spec = 2;  // Send to external network (port 2)
    }

    // NAT translation action for inbound traffic
    action nat_translate_inbound(bit<32> private_ip) {
        // Modify destination IP to private IP
        hdr.ipv4.dstAddr = private_ip;

        // Update checksum (will be recomputed later)
        hdr.ipv4.hdrChecksum = 0;

        // *** FORWARDING LOGIC ADDED HERE ***
        // Forward inbound traffic to internal network interface
        standard_metadata.egress_spec = 1;  // Send to internal network (port 1)
    }

    table nat_outbound {
        key = {
            hdr.ipv4.srcAddr: exact;
            // Would include transport protocol and port in real implementation
        }
        actions = {
            nat_translate_outbound; // Action signature updated implicitly
            drop;
        }
        size = 1024;
    }

    table nat_inbound {
        key = {
            hdr.ipv4.dstAddr: exact;
            // Would include transport protocol and port in real implementation
        }
        actions = {
            nat_translate_inbound;
            drop;
        }
        size = 1024;
    }

    // *** NEW DEFAULT FORWARDING ACTION ***
    // This is used if no NAT translation is performed but we still want to forward
    action forward_packet(bit<9> egress_port) {
        standard_metadata.egress_spec = egress_port;
    }

    apply {
        if (hdr.ipv4.isValid()) {
            // Decrement TTL
            hdr.ipv4.ttl = hdr.ipv4.ttl - 1;

            // If packet from internal network to external
            if (standard_metadata.ingress_port == 1) {
                nat_outbound.apply();
            }
            // If packet from external network to internal
            else if (standard_metadata.ingress_port == 2) {
                nat_inbound.apply();
            }

            // *** CATCH ALL FORWARDING ***
            // If the packet hasn't been assigned an egress port yet
            // (which would happen if it didn't match a NAT rule)
            if (standard_metadata.egress_spec == 0) {
                // Simple forwarding: swap internal and external interfaces
                if (standard_metadata.ingress_port == 1) {
                    forward_packet(2);  // From internal to external
                } else if (standard_metadata.ingress_port == 2) {
                    forward_packet(1);  // From external to internal
                } else {
                    // For any other ports, drop the packet
                    drop();
                }
            }

            // Drop packet if TTL reaches zero
            if (hdr.ipv4.ttl == 0) {
                drop();
            }
        }
    }
}

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version,
              hdr.ipv4.ihl,
              hdr.ipv4.diffserv,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
    }
}

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;