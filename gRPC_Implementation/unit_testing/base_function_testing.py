# client_test.py
import sys
sys.path.insert(0, "..") 
import time
from client import Client

def main():
    client = Client(host="127.0.0.1", port=50051)

    if not client.connect():
        print("[TEST] Could not connect to the gRPC server.")
        return

    print("=== 1) Create Account for 'alice' ===")
    alice_token_hex = client.CreateAccount("alice", "alice_pass")
    print(f"[TEST] Alice's session token = {alice_token_hex[:8]}...")

    print("=== 2) Create Account for 'bob' ===")
    bob_token_hex = client.CreateAccount("bob", "bob_pass")
    print(f"[TEST] Bob's session token = {bob_token_hex[:8]}...")

    print("=== 3) Login as 'alice' ===")
    success_alice, alice_token_logged, unread_alice = client.Login("alice", "alice_pass")
    print(f"[TEST] Login(alice) => success={success_alice}, token={alice_token_logged[:8]}..., unread={unread_alice}")

    print("=== 4) Login as 'bob' ===")
    success_bob, bob_token_logged, unread_bob = client.Login("bob", "bob_pass")
    print(f"[TEST] Login(bob) => success={success_bob}, token={bob_token_logged[:8]}..., unread={unread_bob}")

    # Optional: find their user IDs using GetUserByUsername
    print("=== 5) GetUserByUsername('alice') ===")
    found_alice, alice_id = client.GetUserByUsername("alice")
    print(f"[TEST] Found 'alice'? {found_alice}, user_id={alice_id}")

    print("=== 6) GetUserByUsername('bob') ===")
    found_bob, bob_id = client.GetUserByUsername("bob")
    print(f"[TEST] Found 'bob'? {found_bob}, user_id={bob_id}")

    # 7) ListAccounts with Alice's session (just to see how it works)
    if alice_id and success_alice:
        print("=== 7) ListAccounts (Alice) ===")
        accounts = client.ListAccounts(alice_id, alice_token_logged, wildcard="")
        print(f"[TEST] ListAccounts => {accounts}")

    # 8) Send a message from alice -> bob
    print("=== 8) SendMessage from Alice -> Bob ===")
    if alice_id and success_alice and bob_id:
        sent_ok = client.SendMessage(
            sender_user_id=alice_id,
            session_token=alice_token_logged,
            recipient_user_id=bob_id,
            message_content="Hello Bob!"
        )
        print(f"[TEST] SendMessage => success={sent_ok}")

    # 9) DisplayConversation from Alice's perspective
    print("=== 9) DisplayConversation (Alice->Bob) ===")
    if alice_id and success_alice and bob_id:
        conv = client.DisplayConversation(user_id=alice_id, session_token=alice_token_logged, conversant_id=bob_id)
        print(f"[TEST] Conversation => {conv}")
        # Typically it shows [(msg_id, "Hello Bob!", is_sender=True), ...]

    # For the sake of demonstration, let's pick out the message_id we just sent:
    if conv:
        first_msg_id = conv[0][0]  # The message_id of the first/only message

        # 10) GetUnreadMessages for Bob
        print("=== 10) GetUnreadMessages (Bob) ===")
        if bob_id and success_bob:
            unread_list = client.GetUnreadMessages(bob_id, bob_token_logged)
            print(f"[TEST] Bob's unread => {unread_list}")

            # 11) GetMessageInformation (Bob checks the message details)
            print("=== 11) GetMessageInformation ===")
            has_read, sender_id, content_len, content = client.GetMessageInformation(
                user_id=bob_id,
                session_token=bob_token_logged,
                message_uid=first_msg_id
            )
            print(f"[TEST] has_read={has_read}, sender_id={sender_id}, content_len={content_len}, content={content}")

            # 12) MarkMessageAsRead (Bob marks that message)
            print("=== 12) MarkMessageAsRead ===")
            client.MarkMessageAsRead(
                user_id=bob_id,
                session_token=bob_token_logged,
                message_uid=first_msg_id
            )
            print("[TEST] Marked the message as read.")

            # 13) DisplayConversation again to see if Bob's perspective changes
            print("=== 13) DisplayConversation from Bob's perspective ===")
            bob_conv = client.DisplayConversation(bob_id, bob_token_logged, alice_id)
            print(f"[TEST] Bob's conversation => {bob_conv}")

        # 14) Delete the message (Alice or Bob can do it, let's do Bob)
        print("=== 14) DeleteMessage (Bob) ===")
        client.DeleteMessage(user_id=bob_id, message_uid=first_msg_id, session_token=bob_token_logged)
        print("[TEST] Deleted the message.")

    # 15) GetUsernameByID for Bob
    print("=== 15) GetUsernameByID(bob_id) ===")
    if bob_id:
        bob_name = client.GetUsernameByID(bob_id)
        print(f"[TEST] Username for ID {bob_id} is '{bob_name}'")

    # 16) Delete Bob's account
    print("=== 16) DeleteAccount(bob) ===")
    if bob_id and success_bob:
        client.DeleteAccount(user_id=bob_id, session_token=bob_token_logged)
        print("[TEST] Deleted bob's account.")

    # 17) Delete Alice's account
    print("=== 17) DeleteAccount(alice) ===")
    if alice_id and success_alice:
        client.DeleteAccount(user_id=alice_id, session_token=alice_token_logged)
        print("[TEST] Deleted alice's account.")

    # Done
    client.disconnect()
    print("[TEST] Finished all tests.")


if __name__ == "__main__":
    main()

