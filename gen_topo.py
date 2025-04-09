import json
import sys
import os

def ip_octets(index):
    x = (index - 1) // 254
    y = (index - 1) % 254 + 1

    if x > 254:
        raise ValueError("Too many routers for IP allocation")

    return x, y

def generate_topology(n):
    if n < 2:
        raise ValueError("Topology requires at least 2 routers.")

    output_dir = f"{n}_ring_topo"
    os.makedirs(output_dir, exist_ok=True)

    data = {
        "hosts": {},
        "switches": {},
        "links": []
    }

    for i in range(1, n + 1):
        host_name = f"h{i}"
        switch_name = f"s{i}"
        x, y = ip_octets(i)
        subnet = f"10.{x}.{y}.0/24"
        host_ip = f"10.{x}.{y}.{y}/24" 
        gw_ip   = f"10.{x}.{y}.254"
        host_mac = f"08:00:00:00:{x:02}:{y:02}"

        data["hosts"][host_name] = {
            "ip": host_ip,
            "mac": host_mac,
            "commands": [
                f"route add default gw {gw_ip} dev eth0",
                f"arp -i eth0 -s {gw_ip} 08:{x:02}:{y:02}:00:00:00"
            ]
        }

        data["switches"][switch_name] = {
            "runtime_json": f"{output_dir}/{switch_name}-runtime.json"
        }

        # Host to switch
        data["links"].append([host_name, f"{switch_name}-p1"])

    # Switch-switch links
    for i in range(1, n):
        data["links"].append([f"s{i}-p2", f"s{i+1}-p3"])

    # If it's a ring, connect last to first
    if n > 2:
        data["links"].append([f"s{n}-p2", f"s1-p3"])

    output_path = os.path.join(output_dir, "topology.json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)

def generate_switch_runtime(n):
    output_dir = f"{n}_ring_topo"
    os.makedirs(output_dir, exist_ok=True)

    for i in range(1, n + 1):
        switch_name = f"s{i}"
        switch_runtime = {
            "target": "bmv2",
            "p4info": "build/basic.p4.p4info.txtpb",
            "bmv2_json": "build/basic.json",
            "table_entries": []
        }

        for j in range(1, n + 1):
            x, y = ip_octets(j)
            host_ip = f"10.{x}.{y}.{y}"
            host_mac = f"08:00:00:00:{x:02x}:{y:02x}" 
            gw_mac = f"08:{x:02}:{y:02}:00:00:00"
            
            # route to corresponding host if numbers match up
            if i == j:
                switch_runtime["table_entries"].append({
                    "table": "MyIngress.ipv4_lpm",
                    "match": {
                        "hdr.ipv4.dstAddr": [
                            host_ip,
                            32
                        ]
                    },
                    "action_name": "MyIngress.ipv4_forward",
                    "action_params": {
                        "dstAddr": host_mac,
                        "port": 1
                    }
                })
            else:
                # forward other packets along the ring
                switch_runtime["table_entries"].append({
                    "table": "MyIngress.ipv4_lpm",
                    "match": {
                        "hdr.ipv4.dstAddr": [
                            host_ip,
                            32
                        ]
                    },
                    "action_name": "MyIngress.ipv4_forward",
                    "action_params": {
                        "dstAddr": gw_mac,
                        "port": 2
                    }
                })

        # drop unmatched packets
        switch_runtime["table_entries"].append({
            "table": "MyIngress.ipv4_lpm",
            "default_action": True,
            "action_name": "MyIngress.drop",
            "action_params": {}
        })

        # Write the switch runtime JSON file
        output_path = os.path.join(output_dir, f"{switch_name}-runtime.json")
        with open(output_path, "w") as f:
            json.dump(switch_runtime, f, indent=4)


def generate_topo_file(n, output_path="topo"):
    output_dir = f"{n}_ring_tcp"
    os.makedirs(output_dir, exist_ok=True)
    # Initializing tracked switches and untracked hosts
    tracked = list(range(1, n + 1))  # Switches 1 to n
    untracked = [100 + i for i in range(1, n + 1)]  # Hosts 101 to 100 + n
    
    topo = {}
    
    # Creating the connections in a consistent pattern
    for switch_idx in range(len(tracked)):
        topo[str(tracked[switch_idx])] = {}
        topo[str(tracked[switch_idx])]["1"] = str(untracked[switch_idx])
        if switch_idx < n - 1:
            topo[str(tracked[switch_idx])]["2"] = str(tracked[switch_idx + 1])
        else:
            topo[str(tracked[switch_idx])]["2"] = str(tracked[0])
        
        topo[str(tracked[switch_idx])]["3"] = str(tracked[switch_idx - 1])

    # For hosts, we just connect them to their respective switches
    for i, host in enumerate(untracked):
        topo[str(host)] = {"1": str(tracked[i])}  # Each host connects to its corresponding switch
    
    # Constructing the final data structure
    data = {
        "tracked": tracked,
        "untracked": untracked,
        "topo": topo
    }

    output_path = os.path.join(output_dir, output_path)
    # Writing to JSON file
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_topology.py <number_of_routers>")
        sys.exit(1)
    if int(sys.argv[1]) < 3:
        print("Invalid input, must be greater than 2")
        sys.exit(1)
    try:
        num_routers = int(sys.argv[1])
        generate_topology(num_routers)
        generate_switch_runtime(num_routers)
        generate_topo_file(num_routers)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
