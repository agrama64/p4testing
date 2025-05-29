import json
import sys
import os
import math

def ip_octets(index):
    """Convert node index to IP octets for addressing"""
    x = (index - 1) // 254
    y = (index - 1) % 254 + 1

    if x > 254:
        raise ValueError("Too many nodes for IP allocation")

    return x, y

def generate_tree_topology(layers):
    """Generate a binary tree topology with the specified number of layers"""
    if layers < 1:
        raise ValueError("Tree must have at least 1 layer")

    # Calculate the number of switches in the tree
    num_switches = 2**layers - 1
    
    output_dir = f"{layers}_layer_tree_topo"
    os.makedirs(output_dir, exist_ok=True)

    data = {
        "hosts": {},
        "switches": {},
        "links": []
    }

    # Create switches and hosts
    for i in range(1, num_switches + 1):
        host_name = f"h{i}"
        switch_name = f"s{i}"
        x, y = ip_octets(i)
        subnet = f"10.{x}.{y}.0/24"
        host_ip = f"10.{x}.{y}.{y}/24" 
        gw_ip = f"10.{x}.{y}.254"
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

        # Host to switch link (always port 1)
        data["links"].append([host_name, f"{switch_name}-p1"])

    # Create the tree links
    for i in range(1, num_switches + 1):
        # Connect to left child if it exists
        left_child = 2 * i
        if left_child <= num_switches:
            data["links"].append([f"s{i}-p3", f"s{left_child}-p2"])
        
        # Connect to right child if it exists
        right_child = 2 * i + 1
        if right_child <= num_switches:
            data["links"].append([f"s{i}-p4", f"s{right_child}-p2"])

    output_path = os.path.join(output_dir, "topology.json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)
    
    return num_switches

def get_path_to_node(src, dst, total_nodes):
    """Determine the path from src to dst in the binary tree"""
    if src == dst:
        return []
    
    # Find the path from root to src
    path_to_src = []
    node = src
    while node > 1:
        parent = node // 2
        path_to_src.insert(0, parent)
        node = parent
    
    # Find the path from root to dst
    path_to_dst = []
    node = dst
    while node >= 1:
        path_to_dst.insert(0, node)
        if node == 1:  # Reached root
            break
        node = node // 2
    
    # Find the lowest common ancestor (LCA)
    lca_idx = 0
    while lca_idx < min(len(path_to_src), len(path_to_dst)) and path_to_src[lca_idx] == path_to_dst[lca_idx]:
        lca_idx += 1
    
    # Construct the path: from src up to LCA, then down to dst
    path = []
    
    # Go up from src to LCA
    node = src
    while node != path_to_dst[lca_idx-1]:
        path.append(node // 2)  # Add parent
        node = node // 2
    
    # Go down from LCA to dst
    for i in range(lca_idx, len(path_to_dst)):
        path.append(path_to_dst[i])
    
    return path

def get_next_hop(src, dst, total_nodes):
    """Determine the next hop and port for routing from src to dst in a binary tree"""
    # Case 1: Source and destination are the same - send to connected host
    if src == dst:
        return src, 1  # Port 1 connects to host
    
    # Find the direction to go
    if is_ancestor(src, dst):
        # Destination is in source's subtree
        # Determine if it's in left or right subtree
        if is_in_left_subtree(src, dst):
            return 2 * src, 3  # Go to left child via port 3
        else:
            return 2 * src + 1, 4  # Go to right child via port 4
    else:
        # Need to go up the tree
        return src // 2, 2  # Go to parent via port 2

def is_ancestor(node, descendant):
    """Check if node is an ancestor of descendant"""
    if node > descendant:
        return False
    
    while descendant > node:
        descendant //= 2
    
    return node == descendant

def is_in_left_subtree(parent, node):
    """Check if node is in the left subtree of parent"""
    # First ensure node is in the subtree of parent
    if not is_ancestor(parent, node):
        return False
    
    # Find the immediate child of parent that is an ancestor of node
    while node > 2 * parent:
        node //= 2
    
    # If this child is the left child of parent
    return node == 2 * parent

def generate_switch_runtime(layers):
    """Generate the switch runtime configurations for the tree topology"""
    # Calculate the number of switches
    num_switches = 2**layers - 1
    
    output_dir = f"{layers}_layer_tree_topo"
    os.makedirs(output_dir, exist_ok=True)

    for i in range(1, num_switches + 1):
        switch_name = f"s{i}"
        switch_runtime = {
            "target": "bmv2",
            "p4info": "build/basic.p4.p4info.txtpb",
            "bmv2_json": "build/basic.json",
            "table_entries": []
        }

        # Add entries for each host
        for j in range(1, num_switches + 1):
            x, y = ip_octets(j)
            host_ip = f"10.{x}.{y}.{y}"
            host_mac = f"08:00:00:00:{x:02x}:{y:02x}"
            gw_mac = f"08:{x:02}:{y:02}:00:00:00"
            
            # Direct connection to attached host
            if i == j:
                switch_runtime["table_entries"].append({
                    "table": "MyIngress.ipv4_lpm",
                    "match": {
                        "hdr.ipv4.dstAddr": [host_ip, 32]
                    },
                    "action_name": "MyIngress.ipv4_forward",
                    "action_params": {
                        "dstAddr": host_mac,
                        "port": 1
                    }
                })
            else:
                # For other hosts, determine next hop based on tree structure
                next_hop, port = get_next_hop(i, j, num_switches)
                
                # If next hop is j, then j must be directly connected
                next_x, next_y = ip_octets(next_hop)
                next_hop_mac = f"08:{next_x:02}:{next_y:02}:00:00:00"
                
                switch_runtime["table_entries"].append({
                    "table": "MyIngress.ipv4_lpm",
                    "match": {
                        "hdr.ipv4.dstAddr": [host_ip, 32]
                    },
                    "action_name": "MyIngress.ipv4_forward",
                    "action_params": {
                        "dstAddr": next_hop_mac,
                        "port": port
                    }
                })

        # Add default drop action
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

def generate_topo_file(layers, output_path="topo"):
    """Generate the topology file for the BDD framework"""
    # Calculate the number of switches
    num_switches = 2**layers - 1
    
    output_dir = f"{layers}_layer_tree_topo"
    os.makedirs(output_dir, exist_ok=True)
    
    # Switches are 1 to num_switches, hosts are 101 to 100+num_switches
    tracked = list(range(1, num_switches + 1))
    untracked = [100 + i for i in range(1, num_switches + 1)]
    
    topo = {}
    
    # Create switch entries
    for switch_idx in range(1, num_switches + 1):
        topo[str(switch_idx)] = {}
        
        # Connection to host
        topo[str(switch_idx)]["1"] = str(100 + switch_idx)
        
        # Connection to parent (except root)
        if switch_idx > 1:
            parent = switch_idx // 2
            topo[str(switch_idx)]["2"] = str(parent)
        
        # Connection to left child
        left_child = 2 * switch_idx
        if left_child <= num_switches:
            topo[str(switch_idx)]["3"] = str(left_child)
        
        # Connection to right child
        right_child = 2 * switch_idx + 1
        if right_child <= num_switches:
            topo[str(switch_idx)]["4"] = str(right_child)
    
    # Create host entries
    for host_idx in range(1, num_switches + 1):
        host_id = 100 + host_idx
        topo[str(host_id)] = {"1": str(host_idx)}
    
    # Final data structure
    data = {
        "tracked": tracked,
        "untracked": untracked,
        "topo": topo
    }
    
    output_path = os.path.join(output_dir, output_path)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python gen_tree.py <number_of_layers>")
        sys.exit(1)
    
    try:
        num_layers = int(sys.argv[1])
        if num_layers < 1:
            print("Invalid input, must be at least 1 layer")
            sys.exit(1)
        
        num_switches = generate_tree_topology(num_layers)
        print(f"Generated binary tree topology with {num_layers} layers ({num_switches} switches and hosts)")
        
        generate_switch_runtime(num_layers)
        print(f"Generated switch runtime configurations")
        
        generate_topo_file(num_layers)
        print(f"Generated topology file")
        
        print(f"All files written to {num_layers}_layer_tree_topo/")
        
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)