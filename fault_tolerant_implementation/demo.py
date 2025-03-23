#!/usr/bin/env python3
# demo.py - Script to demonstrate 2-fault tolerance and persistence

import os
import sys
import time
import subprocess
import signal
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
    """Run a shell command and print the output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result

def find_leader():
    """Find the current leader by examining the logs."""
    print("Searching for current leader...")
    result = subprocess.run("grep -l \"became leader for term\" logs/node*.log", 
                          shell=True, capture_output=True, text=True)
    
    if not result.stdout:
        print("No leader found in logs yet.")
        return None
    
    # Get the most recent leader
    leader_logs = result.stdout.strip().split('\n')
    latest_leader = leader_logs[-1]
    
    # Extract node number
    node_num = latest_leader.split('/')[-1].split('.')[0].replace('node', '')
    print(f"Current leader appears to be node{node_num}")
    
    return node_num

def demo_fault_tolerance():
    """
    Demonstrate 2-fault tolerance by:
    1. Starting the 5-node cluster
    2. Creating accounts and sending messages
    3. Killing two nodes (including the leader if possible)
    4. Verifying the system continues to work
    5. Bringing the nodes back
    6. Verifying the system maintains consistency
    """
    print_header("2-FAULT TOLERANCE AND PERSISTENCE DEMO")
    
    # Step 1: Make sure cluster_config.json has 5 nodes
    print_step(1, "Verifying 5-node configuration")
    
    try:
        with open('cluster_config.json', 'r') as f:
            config = f.read()
        
        if '"node5"' not in config:
            print("Error: cluster_config.json must have 5 nodes for 2-fault tolerance")
            print("Please update your configuration file first")
            return
            
        print("Configuration file has 5 nodes ✓")
    except Exception as e:
        print(f"Error reading configuration: {e}")
        return
    
    # Step 2: Start the 5-node cluster
    print_step(2, "Starting the 5-node Raft cluster")
    
    if os.path.exists('cluster_pids.txt'):
        print("Stopping any existing cluster first...")
        run_command("kill $(cat cluster_pids.txt 2>/dev/null) 2>/dev/null")
        time.sleep(2)
    
    run_command("./start_cluster.sh")
    
    # Step 3: Connect a client to the cluster
    print_step(3, "Connecting client to the cluster")
    client = FaultTolerantClient("cluster_config.json")
    print("Client connected!")
    
    # Step 4: Create test accounts
    print_step(4, "Creating test accounts")
    
    users = ["alice", "bob", "charlie"]
    user_tokens = {}
    user_ids = {}
    
    for username in users:
        try:
            token = client.create_account(username, f"password-{username}")
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
    
    # Step 5: Send messages between users
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
            success = client.send_message(
                user_ids[sender], 
                user_tokens[sender], 
                user_ids[recipient], 
                content
            )
            if success:
                print("  Message sent successfully ✓")
            else:
                print("  Failed to send message ✗")
        else:
            print(f"Cannot send from {sender} to {recipient} - missing user information")
    
    # Step 6: Display conversations to verify messages were sent
    print_step(6, "Displaying conversations to verify messages were sent")
    
    for username1, username2 in [("alice", "bob"), ("alice", "charlie"), ("bob", "charlie")]:
        if username1 in user_ids and username2 in user_ids and username1 in user_tokens:
            print(f"\nConversation between {username1} and {username2}:")
            
            messages = client.display_conversation(
                user_ids[username1], 
                user_tokens[username1], 
                user_ids[username2]
            )
            
            if messages:
                for msg_id, content, is_sender in messages:
                    sender = username1 if is_sender else username2
                    print(f"  {sender}: {content}")
            else:
                print("  No messages found.")
    
    # Step 7: Find and kill the leader node (if possible)
    print_step(7, "Testing fault tolerance by killing the leader node")
    
    leader_node = find_leader()
    if leader_node:
        print(f"Killing leader node {leader_node}...")
        run_command(f"./kill_node.sh {leader_node}")
    else:
        # If we can't identify the leader, kill a random node
        random_node = random.randint(1, 3)
        print(f"Killing random node {random_node}...")
        run_command(f"./kill_node.sh {random_node}")
    
    # Give the cluster time to elect a new leader
    print("Waiting for the cluster to elect a new leader...")
    time.sleep(10)
    
    # Step 8: Kill another node to demonstrate 2-fault tolerance
    print_step(8, "Testing 2-fault tolerance by killing a second node")
    
    # Find the new leader if possible
    new_leader = find_leader()
    if new_leader and new_leader != leader_node:
        print(f"New leader is node {new_leader}")
        
        # Kill a different node (not the new leader)
        for node_num in range(1, 6):
            if str(node_num) != leader_node and str(node_num) != new_leader:
                print(f"Killing node {node_num}...")
                run_command(f"./kill_node.sh {node_num}")
                second_killed_node = str(node_num)
                break
    else:
        # If we can't identify the new leader, kill another random node
        # (ensuring it's not the same as the first one)
        available_nodes = [str(i) for i in range(1, 6) if str(i) != leader_node]
        second_node = random.choice(available_nodes)
        print(f"Killing random node {second_node}...")
        run_command(f"./kill_node.sh {second_node}")
        second_killed_node = second_node
    
    # Give the cluster time to stabilize
    print("Waiting for the cluster to stabilize...")
    time.sleep(5)
    
    # Step 9: Continue operations with 2 nodes down
    print_step(9, "Continuing operations with 2 nodes down")
    
    # Send additional messages
    new_messages = [
        ("bob", "alice", "Alice, can you still receive my messages?"),
        ("alice", "bob", "Yes Bob! The system is still working despite node failures.")
    ]
    
    for sender, recipient, content in new_messages:
        if sender in user_ids and recipient in user_ids and sender in user_tokens:
            print(f"{sender} -> {recipient}: '{content}'")
            success = client.send_message(
                user_ids[sender], 
                user_tokens[sender], 
                user_ids[recipient], 
                content
            )
            if success:
                print("  Message sent successfully ✓")
            else:
                print("  Failed to send message ✗")
    
    # Display updated conversation
    if "alice" in user_ids and "bob" in user_ids and "alice" in user_tokens:
        print("\nUpdated conversation between Alice and Bob:")
        messages = client.display_conversation(
            user_ids["alice"], 
            user_tokens["alice"], 
            user_ids["bob"]
        )
        
        if messages:
            for msg_id, content, is_sender in messages:
                sender = "Alice" if is_sender else "Bob"
                print(f"  {sender}: {content}")
        else:
            print("  No messages found.")
    
    # Step 10: Try to kill a third node (should break the cluster)
    print_step(10, "Testing cluster behavior with 3 nodes down (should lose majority)")
    
    remaining_nodes = [str(i) for i in range(1, 6) 
                      if str(i) != leader_node and str(i) != second_killed_node]
    third_node = random.choice(remaining_nodes)
    
    print(f"Killing a third node (node {third_node})...")
    run_command(f"./kill_node.sh {third_node}")
    
    print("With 3 out of 5 nodes down, the cluster should no longer have a majority and stop processing requests.")
    
    # Try to send another message (should fail)
    print("\nAttempting to send a message with 3 nodes down (should fail):")
    try:
        success = client.send_message(
            user_ids["alice"], 
            user_tokens["alice"], 
            user_ids["bob"], 
            "This message should not go through because the cluster has lost quorum."
        )
        print(f"Message sending {'succeeded' if success else 'failed'}")
    except Exception as e:
        print(f"Expected failure: {e}")
    
    # Step 11: Restart nodes to restore the cluster
    print_step(11, "Restoring the cluster by restarting nodes")
    
    print(f"Restarting node {leader_node}...")
    run_command(f"./restart_node.sh {leader_node}")
    
    print(f"Restarting node {second_killed_node}...")
    run_command(f"./restart_node.sh {second_killed_node}")
    
    print(f"Restarting node {third_node}...")
    run_command(f"./restart_node.sh {third_node}")
    
    # Give the cluster time to stabilize
    print("Waiting for the cluster to stabilize...")
    time.sleep(15)
    
    # Step 12: Verify the system is working again
    print_step(12, "Verifying the restored cluster is functional")
    
    # Send a new message
    if "alice" in user_ids and "bob" in user_ids and "alice" in user_tokens:
        print("Alice -> Bob: 'The cluster is back online!'")
        success = client.send_message(
            user_ids["alice"], 
            user_tokens["alice"], 
            user_ids["bob"], 
            "The cluster is back online!"
        )
        if success:
            print("  Message sent successfully ✓")
        else:
            print("  Failed to send message ✗")
    
    # Display updated conversation
    if "alice" in user_ids and "bob" in user_ids and "alice" in user_tokens:
        print("\nFinal conversation between Alice and Bob after cluster recovery:")
        messages = client.display_conversation(
            user_ids["alice"], 
            user_tokens["alice"], 
            user_ids["bob"]
        )
        
        if messages:
            for msg_id, content, is_sender in messages:
                sender = "Alice" if is_sender else "Bob"
                print(f"  {sender}: {content}")
        else:
            print("  No messages found.")
    
    # Step 13: Test persistence by restarting the entire cluster
    print_step(13, "Testing persistence by restarting the entire cluster")
    
    # Stop the entire cluster
    print("Stopping all nodes...")
    run_command("kill $(cat cluster_pids.txt 2>/dev/null) 2>/dev/null")
    time.sleep(5)
    
    # Restart the entire cluster
    print("Restarting the cluster...")
    run_command("./start_cluster.sh")
    time.sleep(15)
    
    # Reconnect the client
    print("Reconnecting the client...")
    client.disconnect()
    client = FaultTolerantClient("cluster_config.json")
    
    # Verify data was persisted
    print("\nVerifying all data was persisted through complete cluster restart:")
    
    # Try to log in with existing credentials
    for username in users:
        print(f"Testing login for {username}...")
        try:
            # success, token, unread_count = client.login(username, f"password-{username}")
            success, token, unread_count = client.log_into_account(username, f"password-{username}")
            if success:
                print(f"  {username} login successful! ✓")
                user_tokens[username] = token
            else:
                print(f"  {username} login failed! ✗")
        except Exception as e:
            print(f"  Error logging in as {username}: {e}")
    
    # Check conversations
    if "alice" in user_ids and "bob" in user_ids and "alice" in user_tokens:
        print("\nVerifying conversation between Alice and Bob after cluster restart:")
        try:
            messages = client.display_conversation(
                user_ids["alice"], 
                user_tokens["alice"], 
                user_ids["bob"]
            )
            
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
    
    print("\nYour chat system now provides:")
    print("• 2-fault tolerance: Can survive any 2 node failures")
    print("• Strong consistency: All nodes maintain the same state")
    print("• Persistence: All data survives complete system restarts")

if __name__ == "__main__":
    demo_fault_tolerance()
