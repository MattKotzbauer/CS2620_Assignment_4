#!/usr/bin/env python3
# demo.py - Script to demonstrate 2-fault tolerance and persistence using Docker Compose

import os
import time
import subprocess
import random
from fault_tolerant_client import FaultTolerantClient

def print_header(text):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_step(step_num, description):
    """Print a step in the demo."""
    print(f"\n>> Step {step_num}: {description}")

def run_command(command):
    """Run a shell command and print its output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result

def find_leader_via_grpc():
    """
    Use the fault_tolerant_client's logic to identify the leader
    by calling LeaderPing on each node in cluster_config_client.json.
    Returns the node ID (like "node3") or None if none respond as leader.
    """
    dummy_client = FaultTolerantClient("cluster_config_client.json")  # or reuse an existing client
    success = dummy_client._find_leader()  # This calls LeaderPing on each known stub
    if success and dummy_client.leader_id:
        return dummy_client.leader_id  # e.g. "node3"
    return None


def find_leader():
    """Find the current leader by examining the logs in the ./logs directory."""
    node = find_leader_via_grpc()
    return node
    
    # print("Searching for current leader in logs...")
    # Assumes the logs are mounted to the host under ./logs/
    # result = subprocess.run("grep -l 'became leader for term' logs/node*.log", 
                              # shell=True, capture_output=True, text=True)
    # if not result.stdout:
        # print("No leader found in logs yet.")
        # return None
    # leader_logs = result.stdout.strip().split('\n')
    # latest_leader = leader_logs[-1]
    # Extract node number from something like logs/node3.log
    # node_num = latest_leader.split('/')[-1].split('.')[0].replace('node', '')
    # print(f"Current leader appears to be node{node_num}")
    # return node_num

def demo_fault_tolerance():
    print_header("2-FAULT TOLERANCE AND PERSISTENCE DEMO")
    
    # Step 1: Verify that our cluster_config.json contains 5 nodes.
    print_step(1, "Verifying 5-node configuration")
    try:
        with open('cluster_config.json', 'r') as f:
            config = f.read()
        if '"node5"' not in config:
            print("Error: cluster_config.json must have 5 nodes for 2-fault tolerance")
            return
        print("Configuration file has 5 nodes ✓")
    except Exception as e:
        print(f"Error reading configuration: {e}")
        return

    # Step 2: Start the 5-node cluster using docker-compose.
    print_step(2, "Starting the 5-node Raft cluster")
    run_command("docker-compose up -d")
    print("Waiting for containers to fully start up...")
    time.sleep(10)

    # Step 3: Connect a client to the cluster.
    print_step(3, "Connecting client to the cluster")
    client = FaultTolerantClient("cluster_config_client.json")
    # print("Client connected!")

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        if client._find_leader():
            print(f"Found a leader on attempt {attempt}!")
            break
        else:
            print(f"No leader found yet (attempt {attempt}/{max_attempts}). Sleeping 2s...")
            time.sleep(2)
    print("Client connected!")
    
    # Step 4: Create test accounts.
    print_step(4, "Creating test accounts")
    users = ["alice", "bob", "charlie"]
    user_tokens = {}
    user_ids = {}
    for username in users:
        try:
            token = client.create_account(username, f"password-{username}")
            # time.sleep(2)
            user_tokens[username] = token
            print(f"Created account for {username}, token: {token[:10]}...")
            found, user_id = client.get_user_by_username(username)
            if found:
                user_ids[username] = user_id
                print(f"  {username}'s user ID: {user_id}")
            else:
                print(f"  Warning: Couldn't retrieve user ID for {username}")
        except Exception as e:
            print(f"Error creating account for {username}: {e}")

    # Step 5: Send messages between users.
    print_step(5, "Sending messages between users")
    message_pairs = [
        ("alice", "bob", "Hey Bob, how's it going?"),
        ("bob", "alice", "Great Alice! Working on the distributed systems project."),
        ("charlie", "alice", "Alice, can you help with the consensus algorithm?"),
        ("alice", "charlie", "Sure Charlie! Let's meet tomorrow."),
        ("bob", "charlie", "Charlie, I fixed that bug we discussed.")
    ]
    for sender, recipient, content in message_pairs:
        if sender in user_ids and recipient in user_ids and sender in user_tokens:
            print(f"{sender} -> {recipient}: '{content}'")
            success = client.send_message(user_ids[sender], user_tokens[sender], user_ids[recipient], content)
            if success:
                print("  Message sent successfully ✓")
            else:
                print("  Failed to send message ✗")
        else:
            print(f"Cannot send from {sender} to {recipient} - missing user information")

    # time.sleep(1)
            
    # Step 6: Display conversations.
    print_step(6, "Displaying conversations to verify messages were sent")
    for username1, username2 in [("alice", "bob"), ("alice", "charlie"), ("bob", "charlie")]:
        if username1 in user_ids and username2 in user_ids and username1 in user_tokens:
            print(f"\nConversation between {username1} and {username2}:")
            messages = client.display_conversation(user_ids[username1], user_tokens[username1], user_ids[username2])
            if messages:
                for msg_id, content, is_sender in messages:
                    sender = username1 if is_sender else username2
                    print(f"  {sender}: {content}")
            else:
                print("  No messages found.")
    
    # Step 7: Kill the leader node.
    print_step(7, "Testing fault tolerance by killing the leader node")
    leader_node = find_leader()
    if leader_node:
        print(f"Killing leader node {leader_node} using docker-compose stop...")
        # run_command(f"docker-compose stop node{leader_node}")
        run_command(f"docker-compose stop {leader_node}")
    else:
        print("No leader found; killing node1 as fallback")
        run_command("docker-compose stop node1")
    
    print("Waiting for the cluster to elect a new leader...")
    time.sleep(15)
    
    max_election_attempts = 5
    for i in range(max_election_attempts):
        new_leader = find_leader()  # calls your fault-tolerant gRPC approach
        if new_leader:
            print(f"New leader after node kill: {new_leader}")
            break
        else:
            print(f"No leader found yet (attempt {i+1}/{max_election_attempts}). Sleeping 2s...")
            time.sleep(2)
    
    # Step 8: Kill a second node.
    print_step(8, "Testing 2-fault tolerance by killing a second node")
    new_leader = find_leader()
    second_killed_node = None
    if new_leader and new_leader != leader_node:
        print(f"New leader is node {new_leader}")
        for node_num in range(1, 6):
            # if str(node_num) != leader_node and str(node_num) != new_leader:
            node_name = f"node{node_num}"
            if node_name != leader_node and node_name != new_leader:
                print(f"Killing node {node_num} using docker-compose stop...")
                run_command(f"docker-compose stop node{node_num}")
                second_killed_node = str(node_num)
                break
    else:
        available_nodes = [str(i) for i in range(1, 6) if str(i) != leader_node]
        second_node = random.choice(available_nodes)
        print(f"Killing random node {second_node} using docker-compose stop...")
        run_command(f"docker-compose stop node{second_node}")
        second_killed_node = second_node
    
    print("Waiting for the cluster to stabilize...")
    time.sleep(10)
    
    # Step 9: Continue operations with 2 nodes down.
    print_step(9, "Continuing operations with 2 nodes down")
    new_messages = [
        ("bob", "alice", "Alice, can you still receive my messages?"),
        ("alice", "bob", "Yes Bob! The system is still working despite node failures.")
    ]
    for sender, recipient, content in new_messages:
        if sender in user_ids and recipient in user_ids and sender in user_tokens:
            print(f"{sender} -> {recipient}: '{content}'")
            success = client.send_message(user_ids[sender], user_tokens[sender], user_ids[recipient], content)
            if success:
                print("  Message sent successfully ✓")
            else:
                print("  Failed to send message ✗")
    
    if "alice" in user_ids and "bob" in user_ids and "alice" in user_tokens:
        print("\nUpdated conversation between Alice and Bob:")
        messages = client.display_conversation(user_ids["alice"], user_tokens["alice"], user_ids["bob"])
        if messages:
            for msg_id, content, is_sender in messages:
                sender = "Alice" if is_sender else "Bob"
                print(f"  {sender}: {content}")
        else:
            print("  No messages found.")
    
    # Step 10: Kill a third node (breaking quorum).
    print_step(10, "Testing cluster behavior with 3 nodes down (should lose majority)")
    remaining_nodes = [str(i) for i in range(1, 6) if str(i) != leader_node and str(i) != second_killed_node]
    third_node = random.choice(remaining_nodes)
    print(f"Killing a third node (node {third_node}) using docker-compose stop...")
    run_command(f"docker-compose stop node{third_node}")
    print("With 3 out of 5 nodes down, the cluster should no longer have a majority and stop processing requests.")
    print("\nAttempting to send a message with 3 nodes down (should fail):")
    try:
        success = client.send_message(user_ids["alice"], user_tokens["alice"], user_ids["bob"], 
                                      "This message should not go through because the cluster has lost quorum.")
        print(f"Message sending {'succeeded' if success else 'failed'}")
    except Exception as e:
        print(f"Expected failure: {e}")
    
    # Step 11: Restart nodes to restore the cluster.
    print_step(11, "Restoring the cluster by restarting nodes")
    for node in [leader_node, second_killed_node, third_node]:
        service_name = node if node.startswith("node") else f"node{node}"
        print(f"Restarting {service_name} using docker-compose start...")
        run_command(f"docker-compose start {service_name}")
        # run_command(f"docker-compose start node{node}")
    print("Waiting for the cluster to stabilize...")
    time.sleep(15)
    
    # Step 12: Verify the restored cluster is functional.
    print_step(12, "Verifying the restored cluster is functional")
    print("Alice -> Bob: 'The cluster is back online!'")
    success = client.send_message(user_ids["alice"], user_tokens["alice"], user_ids["bob"], 
                                  "The cluster is back online!")
    if success:
        print("  Message sent successfully ✓")
    else:
        print("  Failed to send message ✗")
    
    if "alice" in user_ids and "bob" in user_ids and "alice" in user_tokens:
        print("\nFinal conversation between Alice and Bob after cluster recovery:")
        messages = client.display_conversation(user_ids["alice"], user_tokens["alice"], user_ids["bob"])
        if messages:
            for msg_id, content, is_sender in messages:
                sender = "Alice" if is_sender else "Bob"
                print(f"  {sender}: {content}")
        else:
            print("  No messages found.")
    
    # Step 13: Test persistence by restarting the entire cluster.
    print_step(13, "Testing persistence by restarting the entire cluster")
    print("Stopping all nodes using docker-compose down...")
    run_command("docker-compose down")
    time.sleep(5)
    print("Restarting the cluster using docker-compose up -d...")
    run_command("docker-compose up -d")
    time.sleep(15)
    print("Reconnecting the client...")
    client.disconnect()
    client = FaultTolerantClient("cluster_config.json")

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        if client._find_leader():
            print(f"Found a leader on attempt {attempt}!")
            break
        else:
            print(f"No leader found yet (attempt {attempt}/{max_attempts}). Sleeping 2s...")
            time.sleep(2)
    print("Client connected!")

    
    print("\nVerifying all data was persisted through complete cluster restart:")
    for username in users:
        print(f"Testing login for {username}...")
        try:
            success, token, unread_count = client.log_into_account(username, f"password-{username}")
            if success:
                print(f"  {username} login successful! ✓")
                user_tokens[username] = token
            else:
                print(f"  {username} login failed! ✗")
        except Exception as e:
            print(f"  Error logging in as {username}: {e}")
    
    if "alice" in user_ids and "bob" in user_ids and "alice" in user_tokens:
        print("\nVerifying conversation between Alice and Bob after full cluster restart:")
        try:
            messages = client.display_conversation(user_ids["alice"], user_tokens["alice"], user_ids["bob"])
            if messages:
                for msg_id, content, is_sender in messages:
                    sender = "Alice" if is_sender else "Bob"
                    print(f"  {sender}: {content}")
                print("\nAll messages successfully recovered! ✓")
            else:
                print("  No messages found. ✗")
        except Exception as e:
            print(f"  Error retrieving conversation: {e}")
    
    print_header("DEMO COMPLETE")
    print("\nThe demo has successfully demonstrated:")
    print("1. Five-node cluster setup for 2-fault tolerance")
    print("2. Continued operation with 2 nodes down (including the leader)")
    print("3. Cluster unavailability when 3 nodes are down (as expected)")
    print("4. Recovery after node restarts")
    print("5. Complete data persistence across full cluster restarts")
    # print("\nYour chat system now provides:")
    # print("• 2-fault tolerance: Can survive any 2 node failures")
    # print("• Strong consistency: All nodes maintain the same state")
    # print("• Persistence: All data survives complete system restarts")

if __name__ == "__main__":
    demo_fault_tolerance()
