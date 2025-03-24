# unit_testing/client_test.py

import sys
import os
import time
from typing import Optional

# Insert the parent directory into Python path so we can import client.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PARENT_DIR)

from client import Client


def main():
    client = Client(host="127.0.0.1", port=50051)
    if not client.connect():
        print("[TEST] Could not connect to the gRPC server.")
        return

    try:
        #---------------------------------------------------------------
        # Create multiple accounts: Alice, Bob, Carol
        #---------------------------------------------------------------
        print("\n=== CREATE ACCOUNTS ===")
        alice_token = client.CreateAccount("alice", "alice_pass")
        print(f"[TEST] Created 'alice' => token={alice_token[:8]}...")

        bob_token = client.CreateAccount("bob", "bob_pass")
        print(f"[TEST] Created 'bob' => token={bob_token[:8]}...")

        carol_token = client.CreateAccount("carol", "carol_pass")
        print(f"[TEST] Created 'carol' => token={carol_token[:8]}...")

        #---------------------------------------------------------------
        # Log in each account
        #---------------------------------------------------------------
        print("\n=== LOGIN ===")
        alice_ok, alice_active_token, alice_unread = client.Login("alice", "alice_pass")
        print(f"[TEST] alice => ok={alice_ok}, token={alice_active_token[:8]}..., unread={alice_unread}")

        bob_ok, bob_active_token, bob_unread = client.Login("bob", "bob_pass")
        print(f"[TEST] bob   => ok={bob_ok}, token={bob_active_token[:8]}..., unread={bob_unread}")

        carol_ok, carol_active_token, carol_unread = client.Login("carol", "carol_pass")
        print(f"[TEST] carol => ok={carol_ok}, token={carol_active_token[:8]}..., unread={carol_unread}")

        #---------------------------------------------------------------
        #  Get IDs using GetUserByUsername
        #---------------------------------------------------------------
        def get_user_id(username: str) -> Optional[int]:
            found, uid = client.GetUserByUsername(username)
            return uid if found else None

        alice_id = get_user_id("alice")
        bob_id   = get_user_id("bob")
        carol_id = get_user_id("carol")

        print(f"[TEST] user IDs: alice={alice_id}, bob={bob_id}, carol={carol_id}")

        #---------------------------------------------------------------
        # 1) ALICE sends BOB a message; 2) BOB sends CAROL a message
        #---------------------------------------------------------------
        print("\n=== SEND MESSAGES ===")
        if alice_ok and alice_id and bob_id:
            sent_ok_1 = client.SendMessage(
                sender_user_id=alice_id,
                session_token=alice_active_token,
                recipient_user_id=bob_id,
                message_content="Hi Bob, from Alice!"
            )
            print(f"[TEST] alice->bob => success={sent_ok_1}")

        if bob_ok and bob_id and carol_id:
            sent_ok_2 = client.SendMessage(
                sender_user_id=bob_id,
                session_token=bob_active_token,
                recipient_user_id=carol_id,
                message_content="Hey Carol, it's Bob here."
            )
            print(f"[TEST] bob->carol => success={sent_ok_2}")

        #---------------------------------------------------------------
        # Check BOB's unread messages
        #---------------------------------------------------------------
        if bob_ok and bob_id:
            bob_unread_list = client.GetUnreadMessages(bob_id, bob_active_token)
            print(f"[TEST] Bob unread => {bob_unread_list}")

            # If we have 1 or more unread messages, let's do a read on them.
            if bob_unread_list:
                # We'll read the first message
                first_msg_id = bob_unread_list[0][0]  # message UID
                # Get info about it
                m_has_read, m_sender, m_content_len, m_content = client.GetMessageInformation(
                    user_id=bob_id,
                    session_token=bob_active_token,
                    message_uid=first_msg_id
                )
                print(f"[TEST] Bob's first msg => read={m_has_read}, sender={m_sender}, len={m_content_len}, content='{m_content}'")

                # Mark it as read
                client.MarkMessageAsRead(bob_id, bob_active_token, first_msg_id)
                # Confirm it's read now
                m_has_read2, *_ = client.GetMessageInformation(
                    user_id=bob_id,
                    session_token=bob_active_token,
                    message_uid=first_msg_id
                )
                print(f"[TEST] After MarkMessageAsRead => read={m_has_read2}")

        #---------------------------------------------------------------
        # Check CAROL's unread
        #---------------------------------------------------------------
        if carol_ok and carol_id:
            carol_unread_list = client.GetUnreadMessages(carol_id, carol_active_token)
            print(f"[TEST] Carol unread => {carol_unread_list}")

        #---------------------------------------------------------------
        # Let's have ALICE display conversation with BOB
        #---------------------------------------------------------------
        if alice_id and bob_id and alice_ok:
            conv_alice_bob = client.DisplayConversation(
                user_id=alice_id,
                session_token=alice_active_token,
                conversant_id=bob_id
            )
            print(f"[TEST] alice<->bob => {conv_alice_bob}")

            if conv_alice_bob:
                # Let's pick a message to delete
                msg_to_delete = conv_alice_bob[0][0]  # message_id
                # ALICE tries to delete that message
                client.DeleteMessage(alice_id, msg_to_delete, alice_active_token)
                print(f"[TEST] Alice deleted message {msg_to_delete}")
                # Now confirm that GetMessageInformation returns empty
                info_read, _, _, _ = client.GetMessageInformation(
                    user_id=alice_id,
                    session_token=alice_active_token,
                    message_uid=msg_to_delete
                )
                print(f"[TEST] After delete, read_flag for msg {msg_to_delete} => {info_read} (should be False if not found or empty)")

        #---------------------------------------------------------------
        # Now let's test Deleting an account, then verifying it's gone
        #---------------------------------------------------------------
        print("\n=== DELETE 'carol' ACCOUNT + VALIDATION ===")
        if carol_ok and carol_id:
            client.DeleteAccount(carol_id, carol_active_token)
            print("[TEST] Deleted Carol's account.")
            # Now confirm that GetUsernameByID fails
            carol_name = client.GetUsernameByID(carol_id)
            print(f"[TEST] After deletion, userID={carol_id} => username='{carol_name}' (should be empty).")

            # Confirm that GetUserByUsername fails
            found_carol, c_id2 = client.GetUserByUsername("carol")
            print(f"[TEST] GetUserByUsername('carol') => found={found_carol}, user_id={c_id2} (should be False, None).")

        #---------------------------------------------------------------
        # List Accounts with wildcard to see if 'carol' is truly gone
        #---------------------------------------------------------------
        if alice_id and alice_ok:
            all_accounts = client.ListAccounts(alice_id, alice_active_token, wildcard="")
            print(f"[TEST] ListAccounts => {all_accounts} (carol should be absent)")

        #---------------------------------------------------------------
        # Finally, we can delete alice + bob accounts to clean up
        #---------------------------------------------------------------
        print("\n=== CLEANUP: DELETE REMAINING ACCOUNTS ===")
        if bob_ok and bob_id:
            client.DeleteAccount(bob_id, bob_active_token)
            print("[TEST] Deleted bob's account.")

        if alice_ok and alice_id:
            client.DeleteAccount(alice_id, alice_active_token)
            print("[TEST] Deleted alice's account.")

        print("[TEST] Done with all rigorous checks!")

    finally:
        client.disconnect()
        print("[TEST] Disconnected from the server.")


if __name__ == "__main__":
    main()
