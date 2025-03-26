#!/usr/bin/env python3
import time
import json
import os
import signal
import subprocess
import sys
import grpc
import exp_pb2
import exp_pb2_grpc

def start_server(node_id, port, data_dir):
    """Start a Raft server node"""
    cmd = [
        "python3", "raft_server.py",
        "--node-id", node_id,
        "--port", str(port),
        "--data-dir", data_dir,
        "--config", "cluster_config_test.json"
    ]
    return subprocess.Popen(cmd)

def kill_server(process):
    """Kill a server process"""
    if process:
        process.terminate()
        process.wait()

def clear_data_directories():
    """Clear old data directories"""
    for i in range(1, 6):
        dir_path = f"data/node{i}"
        if os.path.exists(dir_path):
            for file in os.listdir(dir_path):
                os.remove(os.path.join(dir_path, file))

def find_leader():
    """Try to find the current leader by pinging all nodes"""
    for i in range(1, 6):
        try:
            print(f"Checking node{i} on port {50050 + i}...")
            channel = grpc.insecure_channel(f'localhost:{50050 + i}')
            stub = exp_pb2_grpc.RaftServiceStub(channel)
            request = exp_pb2.LeaderPingRequest()
            response = stub.LeaderPing(request, timeout=2)
            if response.is_leader:
                print(f"Found leader: node{i}")
                return f"node{i}", 50050 + i
            else:
                print(f"node{i} is not the leader")
        except Exception as e:
            print(f"Failed to connect to node{i}: {str(e)}")
            continue
    print("No leader found in this round")
    return None, None

def demo_fault_tolerance():
    print("\n=== Starting Fault Tolerance Demo ===")
    print("This demo will show:")
    print("1. Server startup and leader election")
    print("2. System continues working with 1-2 nodes down")
    print("3. System stops when 3 nodes are down (as expected)")
    
    # Clear old data
    clear_data_directories()
    
    # Start all 5 nodes
    servers = {}
    for i in range(1, 6):
        node_id = f"node{i}"
        port = 50050 + i
        data_dir = f"data/{node_id}"
        os.makedirs(data_dir, exist_ok=True)
        servers[node_id] = start_server(node_id, port, data_dir)
        print(f"Started {node_id} on port {port}")
    
    # Wait for leader election
    print("\nWaiting for leader election...")
    time.sleep(30)  # Give more time for leader election
    
    # Try multiple times to find the leader
    leader_found = False
    for attempt in range(3):
        print(f"\nAttempt {attempt + 1} to find leader...")
        leader_id, leader_port = find_leader()
        if leader_id:
            leader_found = True
            break
        time.sleep(2)
        
    if not leader_found:
        print("Failed to find a leader after multiple attempts. Exiting.")
        # Clean up servers before exiting
        for server in servers.values():
            kill_server(server)
        return
    
    # Find the leader
    leader_id, leader_port = find_leader()
    if leader_id:
        print(f"Found leader: {leader_id} on port {leader_port}")
    else:
        print("No leader found.")
        return
    
    # Demo 1: Kill one node
    print("\n=== Demo 1: One Node Down ===")
    node_to_kill = "node1" if leader_id != "node1" else "node2"
    print(f"Killing {node_to_kill}")
    kill_server(servers[node_to_kill])
    time.sleep(2)
    
    # Check if system still works
    print("Checking if system still works")
    leader_id, leader_port = find_leader()
    if leader_id:
        print(f"✓ System working: Current leader: {leader_id}")
    else:
        print("✗ System not working")
    
    # Demo 2: Kill second node
    print("\n=== Demo 2: Two Nodes Down ===")
    node_to_kill = "node2" if "node1" in servers else "node3"
    print(f"Killing {node_to_kill}")
    kill_server(servers[node_to_kill])
    time.sleep(2)
    
    # Check if system still works
    print("Checking if system still works")
    leader_id, leader_port = find_leader()
    if leader_id:
        print(f"✓ System working: Current leader: {leader_id}")
    else:
        print("✗ System not working")
    
    # Demo 3: Kill third node (system should stop)
    print("\n=== Demo 3: Three Nodes Down (Expected Failure) ===")
    remaining_nodes = [n for n in servers.keys() if n not in ["node1", "node2", "node3"]]
    node_to_kill = remaining_nodes[0]
    print(f"Killing {node_to_kill}...")
    kill_server(servers[node_to_kill])
    time.sleep(2)
    
    # Check if system stopped as expected
    print("Checking if system stopped (should not find a leader)")
    leader_id, leader_port = find_leader()
    if not leader_id:
        print("✓ System stopped as expected (no leader elected with 3 nodes down)")
    else:
        print(f"✗ Unexpected: found leader {leader_id} when system should be down")
    
    # Cleanup
    print("\n=== Cleaning Up ===")
    for server in servers.values():
        kill_server(server)
    print("Demo complete!")

if __name__ == "__main__":
    try:
        demo_fault_tolerance()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
        sys.exit(0)
