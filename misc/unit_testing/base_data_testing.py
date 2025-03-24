#!/usr/bin/env python3


import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PARENT_DIR)

import hashlib
import exp_pb2

def measure_message_size(message) -> int:
    """
    Returns the number of bytes used to serialize a protobuf message.
    """
    return len(message.SerializeToString())


def create_sample_data():
    """
    Sample data for populating request and response messages.
    Adjust these as needed for testing.
    """
    return {
        'username': 'test_user',
        'password': 'test_password',
        'message_content': 'Hello, this is a test message!',
        'user_id': 12345,
        'session_token': b'0123456789abcdef',  # 16 bytes (example)
        'message_uid': 67890,
        'recipient_user_id': 54321,
        'additional_usernames': ['alice', 'bob'],
    }


def build_request_messages(data):
    """
    Build each of the gRPC request messages with sample data.
    Return a dict of {name: protobuf_message}.
    """
    password_hash = hashlib.sha256(data['password'].encode()).digest()

    requests = {
        # 1) CreateAccountRequest
        'create_account': exp_pb2.CreateAccountRequest(
            username=data['username'],
            password_hash=password_hash
        ),

        # 2) GetUserByUsernameRequest (a.k.a search_username in your table)
        'search_username': exp_pb2.GetUserByUsernameRequest(
            username=data['username']
        ),

        # 3) LoginRequest (a.k.a log_into_account)
        'log_into_account': exp_pb2.LoginRequest(
            username=data['username'],
            password_hash=password_hash
        ),

        # 4) ListAccountsRequest
        'list_accounts': exp_pb2.ListAccountsRequest(
            user_id=data['user_id'],
            session_token=data['session_token'],
            wildcard="*"
        ),

        # 5) DisplayConversationRequest
        'display_conversation': exp_pb2.DisplayConversationRequest(
            user_id=data['user_id'],
            session_token=data['session_token'],
            conversant_id=data['recipient_user_id']
        ),

        # 6) SendMessageRequest
        'send_message': exp_pb2.SendMessageRequest(
            sender_user_id=data['user_id'],
            session_token=data['session_token'],
            recipient_user_id=data['recipient_user_id'],
            message_content=data['message_content']
        ),

        # 7) ReadMessagesRequest (a.k.a read_message)
        'read_message': exp_pb2.ReadMessagesRequest(
            user_id=data['user_id'],
            session_token=data['session_token'],
            number_of_messages_req=10
        ),

        # 8) DeleteMessageRequest
        'delete_message': exp_pb2.DeleteMessageRequest(
            user_id=data['user_id'],
            message_uid=data['message_uid'],
            session_token=data['session_token']
        ),

        # 9) DeleteAccountRequest
        'delete_account': exp_pb2.DeleteAccountRequest(
            user_id=data['user_id'],
            session_token=data['session_token']
        )
    }

    return requests


def build_response_messages(data):
    """
    Build each of the gRPC response messages with sample data.
    Return a dict of {name: protobuf_message}.
    """
    # For demonstration, we mimic typical data the server might return:
    # e.g., a 32-byte session token, a few usernames in ListAccountsResponse, etc.
    session_token_32 = b'0123456789abcdef0123456789abcdef'  # exactly 32 bytes
    password_hash = hashlib.sha256(data['password'].encode()).digest()

    # Example conversation messages
    conversation_messages = [
        exp_pb2.ConversationMessage(
            message_id=1,
            sender_flag=True,
            content="Hello from user1"
        ),
        exp_pb2.ConversationMessage(
            message_id=2,
            sender_flag=False,
            content="Hello from user2"
        ),
    ]

    responses = {
        # 1) CreateAccountResponse
        'create_account': exp_pb2.CreateAccountResponse(
            session_token=session_token_32
        ),

        # 2) GetUserByUsernameResponse (search_username)
        'search_username': exp_pb2.GetUserByUsernameResponse(
            status=exp_pb2.FOUND,
            user_id=data['user_id']
        ),

        # 3) LoginResponse (log_into_account)
        'log_into_account': exp_pb2.LoginResponse(
            status=exp_pb2.STATUS_SUCCESS,
            session_token=session_token_32,
            unread_count=5
        ),

        # 4) ListAccountsResponse
        'list_accounts': exp_pb2.ListAccountsResponse(
            account_count=len(data['additional_usernames']),
            usernames=data['additional_usernames']
        ),

        # 5) DisplayConversationResponse
        'display_conversation': exp_pb2.DisplayConversationResponse(
            message_count=len(conversation_messages),
            messages=conversation_messages
        ),

        # 6) SendMessageResponse (empty)
        'send_message': exp_pb2.SendMessageResponse(),

        # 7) ReadMessagesResponse (empty)
        'read_message': exp_pb2.ReadMessagesResponse(),

        # 8) DeleteMessageResponse (empty)
        'delete_message': exp_pb2.DeleteMessageResponse(),

        # 9) DeleteAccountResponse (empty)
        'delete_account': exp_pb2.DeleteAccountResponse()
    }

    return responses


def print_table(title, sizes):
    """
    Utility to print a table of message sizes.
    """
    print(f"\n{title}:")
    print("-" * 65)
    print(f"{'Message Type':<25} {'Size (bytes)':>12}")
    print("-" * 65)
    for key, size in sizes.items():
        print(f"{key:<25} {size:>12}")
    print("-" * 65)


def main():
    # 1) Build sample data
    data = create_sample_data()

    # 2) Build & measure request messages
    request_messages = build_request_messages(data)
    request_sizes = {}
    for key, msg in request_messages.items():
        request_sizes[key] = measure_message_size(msg)

    # 3) Build & measure response messages
    response_messages = build_response_messages(data)
    response_sizes = {}
    for key, msg in response_messages.items():
        response_sizes[key] = measure_message_size(msg)

    # 4) Print tables
    print_table("gRPC Request Message Sizes", request_sizes)
    print_table("gRPC Response Message Sizes", response_sizes)


if __name__ == "__main__":
    main()
