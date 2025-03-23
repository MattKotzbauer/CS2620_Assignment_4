#!/usr/bin/env python3
import subprocess
import time
import os
import sys
import psutil
import uuid

# Adjust import path if needed
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PARENT_DIR)

from client import Client

def measure_memory(process: psutil.Process):
    """
    Returns the RSS (resident set size) memory usage in MB of the given process.
    """
    mem_info = process.memory_info()
    rss_mb = mem_info.rss / (1024 * 1024)
    return rss_mb

def do_repeated_operations(client, user_id, session_token, batch_num, num_calls=10):
    """
    Perform repeated gRPC calls on an *existing* account to avoid duplications.
    We can, for example, call SendMessage or ListAccounts multiple times.
    """
    print(f"[TEST] Performing repeated calls in batch #{batch_num}...")

    for i in range(num_calls):
        # Option A: SendMessage, if you have another user to send to
        client.send_message(
            sender_user_id=user_id,
            session_token=session_token,
            recipient_user_id=9999,  # some made-up user ID
            message_content=f"Hello from batch {batch_num}, call {i+1}!"
        )

        # Option B: ListAccounts
        # client.list_accounts(user_id, session_token, "*")

        # Option C: DisplayConversation
        # client.display_conversation(user_id, session_token, conversant_id=9999)

        # Add a small sleep if you want to see memory changes more clearly
        # time.sleep(0.1)

def main():
    # 1) Launch the server as a subprocess
    server_path = os.path.join(PARENT_DIR, "server.py")
    server_proc = subprocess.Popen(
        ["python", server_path, "127.0.0.1", "50051"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("[TEST] Starting server, waiting 2 seconds...")
    time.sleep(2)

    # 2) Wrap the server process with psutil
    server_ps = psutil.Process(server_proc.pid)

    # 3) Create a client & connect
    client = Client(host="127.0.0.1", port=50051)
    if not client.connect():
        print("[TEST] Could not connect to server.")
        server_proc.terminate()
        return

    print("[TEST] Connected to server. Measuring baseline memory...")

    baseline_mem = measure_memory(server_ps)
    print(f"Baseline Server RSS: {baseline_mem:.2f} MB")

    # 4) Create a unique user exactly ONCE, then log in
    unique_username = f"memory_test_user_{uuid.uuid4().hex[:8]}"
    password = "some_secure_pass"
    session_token_hex = client.create_account(unique_username, password)
    print(f"[TEST] Created account => {unique_username}, token={session_token_hex}")

    success, login_token, _ = client.log_into_account(unique_username, password)
    if not success:
        print("[TEST] Login failed. Terminating test.")
        client.disconnect()
        server_proc.terminate()
        return

    print(f"[TEST] Logged in as {unique_username}, token={login_token}")

    # Convert token from hex if needed
    session_token = login_token
    user_id = 12345  # If your driver assigns IDs automatically, you might need to fetch it
                     # (e.g., via client.GetUserByUsername or check server logic).
                     # For now, let's assume it's 12345 or we can do:
    # found, fetched_id = client.get_user_by_username(unique_username)
    # if found: user_id = fetched_id

    # 5) Run repeated operations in multiple batches
    num_batches = 3
    for batch_num in range(1, num_batches + 1):
        do_repeated_operations(client, user_id, session_token, batch_num, num_calls=10)

        # Give the server a moment to process
        time.sleep(1)

        current_mem = measure_memory(server_ps)
        mem_diff = current_mem - baseline_mem

        print(f"\n[TEST] Server RSS after batch #{batch_num}: {current_mem:.2f} MB")
        print(f"      Change from baseline: {mem_diff:.2f} MB")

    # 6) Cleanup
    print("\n[TEST] Disconnecting client and terminating server...")
    client.disconnect()
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()

    print("[TEST] Done.")

if __name__ == "__main__":
    """
    Usage:
        python grpc_alt_memory_test.py

    Make sure you have psutil installed:
        pip install psutil
    """
    main()
