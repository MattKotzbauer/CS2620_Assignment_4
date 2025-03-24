#!/usr/bin/env python3

import sys
import os
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PARENT_DIR)

# Assuming `client.py` is in the parent directory (same place as server.py)
from client import Client

def time_rpc_call(func, *args, **kwargs):
    """
    Measures the time it takes to call an RPC function.
    Returns the elapsed time in seconds.
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return (result, end - start)

def run_repeated_tests():
    """
    1. Create an account & log in once.
    2. Repeatedly call certain RPCs (SendMessage, ListAccounts, etc.) 10 times
       to see if overhead is reduced on subsequent calls.
    3. Print average and total times.
    """
    client = Client(host="127.0.0.1", port=50051)
    if not client.connect():
        print("[TEST] Could not connect to server.")
        return

    print("[TEST] Connected to gRPC server.")

    # 1) Create an account & log in
    username = "repeated_test_user"
    password = "repeated_test_pass"
    session_token_hex = client.create_account(username, password)
    print(f"[TEST] Created account => session_token: {session_token_hex}")

    success, login_token, unread_count = client.log_into_account(username, password)
    if not success:
        print("[TEST] Login failed; cannot proceed with repeated tests.")
        return

    print(f"[TEST] Logged in => token: {login_token}, unread_count: {unread_count}")

    # Convert hex token to pass into subsequent calls
    # (Most of your client methods already expect hex strings, so this might be optional.)
    session_token = login_token

    # 2) Perform repeated calls of certain operations
    repeated_calls = {
        "SendMessage": lambda i: client.send_message(
            sender_user_id=12345,
            session_token=session_token,
            recipient_user_id=54321,
            message_content=f"Repeated call #{i+1}"
        ),
        "ListAccounts": lambda i: client.list_accounts(
            user_id=12345, 
            session_token=session_token, 
            wildcard="*"
        ),
        "DisplayConversation": lambda i: client.display_conversation(
            user_id=12345,
            session_token=session_token,
            conversant_id=54321
        )
    }

    # We will store timing results: {operation_name: [call_times]}
    timing_results = {op: [] for op in repeated_calls.keys()}

    for op_name, func in repeated_calls.items():
        print(f"\n[TEST] Repeated calls for '{op_name}'")
        for i in range(10):
            _, elapsed = time_rpc_call(func, i)
            timing_results[op_name].append(elapsed)
            print(f"  Call #{i+1}: {elapsed:.6f} sec")

    client.disconnect()

    # 3) Print summary of average and total times
    print("\nSummary of repeated call performance:")
    print("-" * 50)
    for op_name, times in timing_results.items():
        total_time = sum(times)
        avg_time = total_time / len(times)
        print(f"{op_name:20s} total: {total_time:.6f} s, average: {avg_time:.6f} s")

    print("[TEST] Completed repeated call tests.")


if __name__ == "__main__":
    # You should have the gRPC server running in a separate terminal,
    # e.g. `python server.py 127.0.0.1 50051`
    run_repeated_tests()
