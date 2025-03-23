# server.py
import sys
from concurrent import futures
import grpc

import driver
import core_entities
import core_structures

# Generated from your exp.proto
import exp_pb2
import exp_pb2_grpc

class MessagingServiceServicer(exp_pb2_grpc.MessagingServiceServicer):
    """
    Functions defined server-side within our gRPC client-server communication: 
     1) CreateAccount
     2) Login
     3) ListAccounts
     4) DisplayConversation
     5) SendMessage
     6) ReadMessages
     7) DeleteMessage
     8) DeleteAccount
     9) GetUnreadMessages
     10) GetMessageInformation
     11) GetUsernameByID
     12) MarkMessageAsRead
     13) GetUserByUsername

    A concise listing of the input / output fields for each of these can be found in exp.proto.
    """

    # --------------------------------------------------------------------------
    # 1) CreateAccount
    # --------------------------------------------------------------------------
    def CreateAccount(self, request, context):
        """
        request: CreateAccountRequest { string username, bytes password_hash }
        returns: CreateAccountResponse { bytes session_token }
        """
        username = request.username
        # Convert the 32-byte hash into a hex string (if your driver expects hex).
        password_hex = request.password_hash.hex()
        
        # Use your driver to create the account and return a session token (hex string).
        session_token_hex = driver.create_account(username, password_hex)
        # Convert that hex token back into bytes for the gRPC response.
        session_token_bytes = bytes.fromhex(session_token_hex)

        return exp_pb2.CreateAccountResponse(session_token=session_token_bytes)

    # --------------------------------------------------------------------------
    # 2) Login
    # --------------------------------------------------------------------------
    def Login(self, request, context):
        """
        request: LoginRequest { string username, bytes password_hash }
        returns: LoginResponse { Status status, bytes session_token, uint32 unread_count }
        """
        username = request.username
        password_hex = request.password_hash.hex()

        # Look up user via driver (e.g., user_trie).
        user = driver.user_trie.trie.get(username)
        if user and driver.check_password(username, password_hex):
            # Valid credentials
            session_token_hex = driver.generate_session_token(user.userID)
            session_token_bytes = bytes.fromhex(session_token_hex)
            unread_count = len(user.unread_messages)

            return exp_pb2.LoginResponse(
                status=exp_pb2.STATUS_SUCCESS,
                session_token=session_token_bytes,
                unread_count=unread_count
            )
        else:
            # Invalid credentials
            return exp_pb2.LoginResponse(
                status=exp_pb2.STATUS_FAILURE,
                session_token=b"",  # or 32 zero-bytes
                unread_count=0
            )

    # --------------------------------------------------------------------------
    # 3) ListAccounts
    # --------------------------------------------------------------------------
    def ListAccounts(self, request, context):
        """
        request: ListAccountsRequest { uint32 user_id, bytes session_token, string wildcard }
        returns: ListAccountsResponse { uint32 account_count, repeated string usernames }
        """
        user_id = request.user_id
        token_from_req = request.session_token.hex()

        # Validate session token
        stored_token = driver.session_tokens.tokens.get(user_id)
        if not stored_token or stored_token != token_from_req:
            # Could abort or return empty if invalid.
            return exp_pb2.ListAccountsResponse(account_count=0, usernames=[])

        # Retrieve matching accounts via wildcard
        matched = driver.list_accounts(request.wildcard)
        return exp_pb2.ListAccountsResponse(
            account_count=len(matched),
            usernames=matched
        )

    # --------------------------------------------------------------------------
    # 4) DisplayConversation
    # --------------------------------------------------------------------------
    def DisplayConversation(self, request, context):
        """
        request: DisplayConversationRequest { user_id, session_token, conversant_id }
        returns: DisplayConversationResponse { message_count, repeated ConversationMessage messages }
        """
        user_id = request.user_id
        token_hex = request.session_token.hex()
        conversant_id = request.conversant_id

        # Check session
        stored_token = driver.session_tokens.tokens.get(user_id)
        if not stored_token or stored_token != token_hex:
            # Invalid session => empty conversation
            return exp_pb2.DisplayConversationResponse(message_count=0, messages=[])

        # Retrieve all messages between user_id and conversant_id
        key = tuple(sorted([user_id, conversant_id]))
        msg_list = driver.conversations.conversations.get(key, [])

        # Convert them into ConversationMessage proto messages
        conv_msgs = []
        for msg in msg_list:
            is_sender = (msg.sender_id == user_id)
            conv_msgs.append(exp_pb2.ConversationMessage(
                message_id=msg.uid,
                sender_flag=is_sender,
                content=msg.contents
            ))

        return exp_pb2.DisplayConversationResponse(
            message_count=len(conv_msgs),
            messages=conv_msgs
        )

    # --------------------------------------------------------------------------
    # 5) SendMessage
    # --------------------------------------------------------------------------
    def SendMessage(self, request, context):
        """
        request: SendMessageRequest { sender_user_id, session_token, recipient_user_id, message_content }
        returns: SendMessageResponse {}
        """
        user_id = request.sender_user_id
        token_hex = request.session_token.hex()
        recipient_id = request.recipient_user_id
        content = request.message_content

        # Validate session
        stored_token = driver.session_tokens.tokens.get(user_id)
        if stored_token and stored_token == token_hex:
            # Deliver message
            driver.send_message(user_id, recipient_id, content)
        else:
            # Invalid token => do nothing or raise
            pass

        return exp_pb2.SendMessageResponse()

    # --------------------------------------------------------------------------
    # 6) ReadMessages
    # --------------------------------------------------------------------------
    def ReadMessages(self, request, context):
        """
        request: ReadMessagesRequest { user_id, session_token, number_of_messages_req }
        returns: ReadMessagesResponse {}
        """
        user_id = request.user_id
        token_hex = request.session_token.hex()
        count = request.number_of_messages_req

        # Validate session
        if driver.session_tokens.tokens.get(user_id) == token_hex:
            driver.read_messages(user_id, count)
        else:
            # Could raise an error or simply do nothing
            pass

        return exp_pb2.ReadMessagesResponse()

    # --------------------------------------------------------------------------
    # 7) DeleteMessage
    # --------------------------------------------------------------------------
    def DeleteMessage(self, request, context):
        """
        request: DeleteMessageRequest { user_id, message_uid, session_token }
        returns: DeleteMessageResponse {}
        """
        user_id = request.user_id
        msg_uid = request.message_uid
        token_hex = request.session_token.hex()

        # Validate session
        if driver.session_tokens.tokens.get(user_id) == token_hex:
            driver.delete_message(msg_uid)

        return exp_pb2.DeleteMessageResponse()

    # --------------------------------------------------------------------------
    # 8) DeleteAccount
    # --------------------------------------------------------------------------
    def DeleteAccount(self, request, context):
        """
        request: DeleteAccountRequest { user_id, session_token }
        returns: DeleteAccountResponse {}
        """
        user_id = request.user_id
        token_hex = request.session_token.hex()

        if driver.session_tokens.tokens.get(user_id) == token_hex:
            driver.delete_account(user_id)

        return exp_pb2.DeleteAccountResponse()

    # --------------------------------------------------------------------------
    # 9) GetUnreadMessages
    # --------------------------------------------------------------------------
    def GetUnreadMessages(self, request, context):
        """
        request: GetUnreadMessagesRequest { user_id, session_token }
        returns: GetUnreadMessagesResponse { count, repeated UnreadMessageInfo messages }
        """
        user_id = request.user_id
        token_hex = request.session_token.hex()

        # Validate session
        if driver.session_tokens.tokens.get(user_id) == token_hex:
            user_obj = driver.user_base.users.get(user_id)
            if user_obj:
                # Gather unread message objects
                unread_uids = list(user_obj.unread_messages)
                unread_msgs = []
                for uid in unread_uids:
                    msg = driver.message_base.messages.get(uid)
                    if msg:
                        unread_msgs.append(exp_pb2.UnreadMessageInfo(
                            message_uid=msg.uid,
                            sender_id=msg.sender_id,
                            receiver_id=msg.receiver_id
                        ))
                return exp_pb2.GetUnreadMessagesResponse(
                    count=len(unread_msgs),
                    messages=unread_msgs
                )

        # If invalid session or user not found, return empty
        return exp_pb2.GetUnreadMessagesResponse(count=0, messages=[])

    # --------------------------------------------------------------------------
    # 10) GetMessageInformation
    # --------------------------------------------------------------------------
    def GetMessageInformation(self, request, context):
        """
        request: GetMessageInformationRequest { user_id, session_token, message_uid }
        returns: GetMessageInformationResponse { bool read_flag, uint32 sender_id, uint32 content_length, string message_content }
        """
        user_id = request.user_id
        msg_uid = request.message_uid
        token_hex = request.session_token.hex()

        if driver.session_tokens.tokens.get(user_id) == token_hex:
            msg = driver.message_base.messages.get(msg_uid)
            if msg:
                content_bytes = msg.contents.encode("utf-8")
                return exp_pb2.GetMessageInformationResponse(
                    read_flag=msg.has_been_read,
                    sender_id=msg.sender_id,
                    content_length=len(content_bytes),
                    message_content=msg.contents
                )

        # Invalid token or no message => empty fallback
        return exp_pb2.GetMessageInformationResponse(
            read_flag=False,
            sender_id=0,
            content_length=0,
            message_content=""
        )

    # --------------------------------------------------------------------------
    # 11) GetUsernameByID
    # --------------------------------------------------------------------------
    def GetUsernameByID(self, request, context):
        """
        request: GetUsernameByIDRequest { user_id }
        returns: GetUsernameByIDResponse { string username }
        """
        user_id = request.user_id
        user_obj = driver.user_base.users.get(user_id)
        if user_obj:
            return exp_pb2.GetUsernameByIDResponse(username=user_obj.username)
        else:
            return exp_pb2.GetUsernameByIDResponse(username="")

    # --------------------------------------------------------------------------
    # 12) MarkMessageAsRead
    # --------------------------------------------------------------------------
    def MarkMessageAsRead(self, request, context):
        """
        request: MarkMessageAsReadRequest { user_id, session_token, message_uid }
        returns: MarkMessageAsReadResponse {}
        """
        user_id = request.user_id
        msg_uid = request.message_uid
        token_hex = request.session_token.hex()

        if driver.session_tokens.tokens.get(user_id) == token_hex:
            # Mark message as read
            user_obj = driver.user_base.users.get(user_id)
            if user_obj:
                user_obj.mark_message_read(msg_uid)
            msg = driver.message_base.messages.get(msg_uid)
            if msg:
                msg.has_been_read = True

        return exp_pb2.MarkMessageAsReadResponse()

    # --------------------------------------------------------------------------
    # 13) GetUserByUsername
    # --------------------------------------------------------------------------
    def GetUserByUsername(self, request, context):
        """
        request: GetUserByUsernameRequest { string username }
        returns: GetUserByUsernameResponse { FoundStatus status, uint32 user_id }
        """
        username = request.username
        user_obj = driver.user_trie.trie.get(username)
        if user_obj:
            return exp_pb2.GetUserByUsernameResponse(
                status=exp_pb2.FOUND,
                user_id=user_obj.userID
            )
        else:
            return exp_pb2.GetUserByUsernameResponse(
                status=exp_pb2.NOT_FOUND,
                user_id=0
            )

def serve(host="127.0.0.1", port=50051):
    """Start the gRPC server and listen on the specified host/port."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    exp_pb2_grpc.add_MessagingServiceServicer_to_server(
        MessagingServiceServicer(),
        server
    )

    address = f"{host}:{port}"
    server.add_insecure_port(address)
    server.start()
    print(f"[gRPC SERVER] Listening on {address} ...")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("[gRPC SERVER] Shutting down.")

if __name__ == "__main__":
    # You can override host/port via command line, e.g.:
    #   python socket_handler.py 0.0.0.0 50051
    args = sys.argv[1:]
    host = args[0] if len(args) > 0 else "127.0.0.1"
    port = int(args[1]) if len(args) > 1 else 50051

    serve(host, port)
