#!/usr/bin/env python3
import os
import sys
import socket

from scapy.all import (
    TCP,
    FieldLenField,
    FieldListField,
    IntField,
    IPOption,
    ShortField,
    get_if_list,
    sniff,
    StrFixedLenField,
    Packet,
    IP
)
from scapy.layers.inet import _IPOption_HDR

class PacketHeader(Packet):
    name = "CustomHeader"
    fields_desc = [
        IntField("packet_id", 0),
        IntField("msg_type", 1),
    ]

def get_if():
    ifs=get_if_list()
    iface=None
    for i in get_if_list():
        if "eth0" in i:
            iface=i
            break;
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface

class IPOption_MRI(IPOption):
    name = "MRI"
    option = 31
    fields_desc = [ _IPOption_HDR,
                    FieldLenField("length", None, fmt="B",
                                  length_of="swids",
                                  adjust=lambda pkt,l:l+4),
                    ShortField("count", 0),
                    FieldListField("swids",
                                   [],
                                   IntField("", 0),
                                   length_from=lambda pkt:pkt.count*4) ]
def handle_pkt(pkt, ip_addr):
    if (IP in pkt) and (pkt[IP].dst == ip_addr):
        print("got a packet at " + str(sys.argv[1]))
        pkt.show2()
    #    hexdump(pkt)
        sys.stdout.flush()


def main():
    if len(sys.argv) < 2:
        print("Pass 1 argument: <desination>")
        exit(1)
    addr = socket.gethostbyname(sys.argv[1])
    ifaces = [i for i in os.listdir('/sys/class/net/') if 'eth' in i]
    iface = ifaces[0]
    print("sniffing on %s" % iface)
    sys.stdout.flush()
    sniff(iface = iface,
          prn = lambda x: handle_pkt(x, addr))

if __name__ == '__main__':
    main()
