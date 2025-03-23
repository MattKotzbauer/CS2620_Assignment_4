# client.py
import grpc
import hashlib
from typing import Optional, Tuple, List

# Protobuf-generated modules from your exp.proto
import exp_pb2
import exp_pb2_grpc


class Client:
    """
    Functions that we define within our gRPC client-server communication: 
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

    (The byte content of each docstring references the original wire protocol (opcodes, length fields),
    but we internally call gRPC methods from exp_pb2_grpc.MessagingServiceStub)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 50051):
        self.host = host
        self.port = port
        self.channel: Optional[grpc.Channel] = None
        self.stub: Optional[exp_pb2_grpc.MessagingServiceStub] = None
        self._connected = False

    def connect(self) -> bool:
        """
        Establish a gRPC channel to the server.
        Returns True if connected, False otherwise.
        """
        if self._connected:
            return True
        try:
            self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
            self.stub = exp_pb2_grpc.MessagingServiceStub(self.channel)

            # Optionally block until the channel is ready
            grpc.channel_ready_future(self.channel).result(timeout=5)
            self._connected = True
            return True
        except Exception as e:
            print(f"[CLIENT] gRPC connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """
        Gracefully close the gRPC channel.
        """
        if self.channel:
            self.channel.close()
        self.channel = None
        self.stub = None
        self._connected = False

    def _ensure_connected(self):
        """
        Utility to ensure the client is connected before an RPC call.
        Raises ConnectionError if unable to connect.
        """
        if not self._connected and not self.connect():
            raise ConnectionError("[CLIENT] Could not connect to gRPC server.")

    # --------------------------------------------------------------------------
    # 1) CreateAccount (Opcode 0x01 -> Response 0x02)
    # --------------------------------------------------------------------------
    def CreateAccount(self, username: str, password: str) -> str:
        """
        Create a new account.

        Wire Protocol (old):
          Request (0x01): 
            4 bytes length, 1 byte opcode, 2 bytes username length, 
            n bytes username, 32 bytes hashed password
          Response (0x02): 
            4 bytes length, 1 byte opcode, 32 bytes session token

        Returns:
            str: The 32-byte session token in hex.
        """
        self._ensure_connected()
        # Hash password -> 32 bytes
        hashed_password = hashlib.sha256(password.encode()).digest()

        request = exp_pb2.CreateAccountRequest(
            username=username,
            password_hash=hashed_password
        )
        response = self.stub.CreateAccount(request)
        return response.session_token.hex()

    # --------------------------------------------------------------------------
    # 2) Login (Opcode 0x03 -> Response 0x04)
    # --------------------------------------------------------------------------
    def Login(self, username: str, password: str) -> Tuple[bool, str, int]:
        """
        Log into an existing account.

        Wire Protocol (old):
          Request (0x03):
            4 bytes length, 1 byte opcode,
            2 bytes username length, n bytes username,
            32 bytes hashed password

          Response (0x04):
            4 bytes length, 1 byte opcode,
            1 byte status (0x00 = success),
            32 bytes session token,
            4 bytes unread count

        Returns:
            (bool, str, int):
            (success, session_token_hex, unread_count)
        """
        self._ensure_connected()
        hashed_password = hashlib.sha256(password.encode()).digest()

        request = exp_pb2.LoginRequest(
            username=username,
            password_hash=hashed_password
        )
        response = self.stub.Login(request)
        success = (response.status == exp_pb2.STATUS_SUCCESS)
        token_hex = response.session_token.hex()
        unread_count = response.unread_count
        return (success, token_hex, unread_count)

    # --------------------------------------------------------------------------
    # 3) ListAccounts (Opcode 0x05 -> Response 0x06)
    # --------------------------------------------------------------------------
    def ListAccounts(self, user_id: int, session_token: str, wildcard: str) -> List[str]:
        """
        List matching accounts.

        Wire Protocol (old):
          Request (0x05):
            4 bytes length, 1 byte opcode,
            2 bytes user ID, 32 bytes session token,
            2 bytes wildcard length, n bytes wildcard

          Response (0x06):
            4 bytes length, 1 byte opcode,
            2 bytes account count,
            for each account: 2 bytes uname length, n bytes username

        Returns:
            List[str]: A list of usernames.
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)

        request = exp_pb2.ListAccountsRequest(
            user_id=user_id,
            session_token=token_bytes,
            wildcard=wildcard
        )
        response = self.stub.ListAccounts(request)
        return list(response.usernames)

    # --------------------------------------------------------------------------
    # 4) DisplayConversation (Opcode 0x07 -> Response 0x08)
    # --------------------------------------------------------------------------
    def DisplayConversation(self, user_id: int, session_token: str, conversant_id: int
                            ) -> List[Tuple[int, str, bool]]:
        """
        Display the conversation between user_id and conversant_id.

        Wire Protocol (old):
          Request (0x07):
            4 bytes length, 1 byte opcode,
            2 bytes user ID, 32 bytes session token,
            2 bytes conversant ID

          Response (0x08):
            4 bytes length, 1 byte opcode,
            4 bytes message count,
            then for each message:
              4 bytes msg ID, 2 bytes msg length,
              1 byte sender flag (0x01 or 0x00),
              n bytes message content

        Returns:
            A list of tuples (message_id, message_content, sender_flag).
            sender_flag = True if the user was the sender, False otherwise.
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)

        request = exp_pb2.DisplayConversationRequest(
            user_id=user_id,
            session_token=token_bytes,
            conversant_id=conversant_id
        )
        response = self.stub.DisplayConversation(request)

        # Convert repeated ConversationMessage -> list of (msg_id, content, is_sender)
        result = []
        for msg in response.messages:
            result.append((msg.message_id, msg.content, msg.sender_flag))
        return result

    # --------------------------------------------------------------------------
    # 5) SendMessage (Opcode 0x09 -> Response 0x0A)
    # --------------------------------------------------------------------------
    def SendMessage(self, sender_user_id: int, session_token: str,
                    recipient_user_id: int, message_content: str) -> bool:
        """
        Send a message to another user.

        Wire Protocol (old):
          Request (0x09):
            4 bytes length, 1 byte opcode,
            2 bytes sender ID, 32 bytes session token,
            2 bytes recipient ID, 2 bytes msg length,
            n bytes message content

          Response (0x0A):
            4 bytes length, 1 byte opcode

        Returns:
            bool: True if sent successfully, False otherwise.
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)
        if len(token_bytes) != 32:
            print(f"[CLIENT] Invalid session token length: {len(token_bytes)}")
            return False

        request = exp_pb2.SendMessageRequest(
            sender_user_id=sender_user_id,
            session_token=token_bytes,
            recipient_user_id=recipient_user_id,
            message_content=message_content
        )
        try:
            self.stub.SendMessage(request)
            return True
        except grpc.RpcError as e:
            print(f"[CLIENT] Failed to send message: {e}")
            return False

    # --------------------------------------------------------------------------
    # 6) ReadMessages (Opcode 0x0B -> Response 0x0C)
    # --------------------------------------------------------------------------
    def ReadMessages(self, user_id: int, session_token: str, number_of_messages_req: int) -> None:
        """
        Read/acknowledge a given number of messages.

        Wire Protocol (old):
          Request (0x0B):
            4 bytes length, 1 byte opcode,
            2 bytes user ID, 32 bytes session token,
            4 bytes number_of_messages_req

          Response (0x0C):
            4 bytes length, 1 byte opcode
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)

        request = exp_pb2.ReadMessagesRequest(
            user_id=user_id,
            session_token=token_bytes,
            number_of_messages_req=number_of_messages_req
        )
        self.stub.ReadMessages(request)

    # --------------------------------------------------------------------------
    # 7) DeleteMessage (Opcode 0x0D -> Response 0x0E)
    # --------------------------------------------------------------------------
    def DeleteMessage(self, user_id: int, message_uid: int, session_token: str) -> None:
        """
        Delete a specific message.

        Wire Protocol (old):
          Request (0x0D):
            4 bytes length, 1 byte opcode,
            2 bytes user ID, 4 bytes msg UID,
            32 bytes session token

          Response (0x0E):
            4 bytes length, 1 byte opcode
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)

        request = exp_pb2.DeleteMessageRequest(
            user_id=user_id,
            message_uid=message_uid,
            session_token=token_bytes
        )
        self.stub.DeleteMessage(request)

    # --------------------------------------------------------------------------
    # 8) DeleteAccount (Opcode 0x0F -> Response 0x10)
    # --------------------------------------------------------------------------
    def DeleteAccount(self, user_id: int, session_token: str) -> None:
        """
        Delete the specified account.

        Wire Protocol (old):
          Request (0x0F):
            4 bytes length, 1 byte opcode,
            2 bytes user ID, 32 bytes session token

          Response (0x10):
            4 bytes length, 1 byte opcode
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)

        request = exp_pb2.DeleteAccountRequest(
            user_id=user_id,
            session_token=token_bytes
        )
        self.stub.DeleteAccount(request)

    # --------------------------------------------------------------------------
    # 9) GetUnreadMessages (Opcode 0x11 -> Response 0x12)
    # --------------------------------------------------------------------------
    def GetUnreadMessages(self, user_id: int, session_token: str
                          ) -> List[Tuple[int, int, int]]:
        """
        Fetch unread messages for a user.

        Wire Protocol (old):
          Request (0x11):
            4 bytes length, 1 byte opcode,
            2 bytes user ID, 32 bytes session token

          Response (0x12):
            4 bytes length, 1 byte opcode,
            4 bytes count,
            then for each: 4 bytes msg UID, 2 bytes sender ID, 2 bytes receiver ID

        Returns:
            A list of (message_uid, sender_id, receiver_id).
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)

        request = exp_pb2.GetUnreadMessagesRequest(
            user_id=user_id,
            session_token=token_bytes
        )
        resp = self.stub.GetUnreadMessages(request)

        results = []
        for m in resp.messages:
            results.append((m.message_uid, m.sender_id, m.receiver_id))
        return results

    # --------------------------------------------------------------------------
    # 10) GetMessageInformation (Opcode 0x13 -> Response 0x14)
    # --------------------------------------------------------------------------
    def GetMessageInformation(self, user_id: int, session_token: str,
                              message_uid: int) -> Tuple[bool, int, int, str]:
        """
        Get message info (read status, sender ID, content length, content).

        Wire Protocol (old):
          Request (0x13):
            4 bytes length, 1 byte opcode,
            2 bytes user ID, 32 bytes session token,
            4 bytes message UID

          Response (0x14):
            4 bytes length, 1 byte opcode,
            1 byte read flag,
            2 bytes sender ID,
            2 bytes content length,
            n bytes message content

        Returns:
            (bool, int, int, str):
              (read_flag, sender_id, content_length, message_content)
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)

        request = exp_pb2.GetMessageInformationRequest(
            user_id=user_id,
            session_token=token_bytes,
            message_uid=message_uid
        )
        resp = self.stub.GetMessageInformation(request)
        # read_flag, sender_id, content_length, message_content
        return (resp.read_flag, resp.sender_id, resp.content_length, resp.message_content)

    # --------------------------------------------------------------------------
    # 11) GetUsernameByID (Opcode 0x15 -> Response 0x16)
    # --------------------------------------------------------------------------
    def GetUsernameByID(self, user_id: int) -> str:
        """
        Get username from a user ID.

        Wire Protocol (old):
          Request (0x15):
            4 bytes length, 1 byte opcode,
            2 bytes user ID

          Response (0x16):
            4 bytes length, 1 byte opcode,
            2 bytes username length,
            n bytes username

        Returns:
            str: The username, or empty string if not found.
        """
        self._ensure_connected()
        request = exp_pb2.GetUsernameByIDRequest(user_id=user_id)
        resp = self.stub.GetUsernameByID(request)
        return resp.username

    # --------------------------------------------------------------------------
    # 12) MarkMessageAsRead (Opcode 0x17 -> Response 0x18)
    # --------------------------------------------------------------------------
    def MarkMessageAsRead(self, user_id: int, session_token: str, message_uid: int) -> None:
        """
        Mark the specified message as read.

        Wire Protocol (old):
          Request (0x17):
            4 bytes length, 1 byte opcode,
            2 bytes user ID, 32 bytes session token,
            4 bytes message UID

          Response (0x18):
            4 bytes length, 1 byte opcode
        """
        self._ensure_connected()
        token_bytes = bytes.fromhex(session_token)

        request = exp_pb2.MarkMessageAsReadRequest(
            user_id=user_id,
            session_token=token_bytes,
            message_uid=message_uid
        )
        self.stub.MarkMessageAsRead(request)

    # --------------------------------------------------------------------------
    # 13) GetUserByUsername (Opcode 0x19 -> Response 0x1A)
    # --------------------------------------------------------------------------
    def GetUserByUsername(self, username: str) -> Tuple[bool, Optional[int]]:
        """
        Retrieve a user by username.

        Wire Protocol (old):
          Request (0x19):
            4 bytes length, 1 byte opcode,
            2 bytes username length,
            n bytes username

          Response (0x1A):
            4 bytes length, 1 byte opcode,
            1 byte status (0x00=found, 0x01=not),
            if found -> 2 bytes user ID

        Returns:
            (found: bool, user_id: int|None)
        """
        self._ensure_connected()
        request = exp_pb2.GetUserByUsernameRequest(username=username)
        resp = self.stub.GetUserByUsername(request)

        if resp.status == exp_pb2.FOUND:
            return (True, resp.user_id)
        else:
            return (False, None)

    def create_account(self, username, password):
        return self.CreateAccount(username, password)

    def log_into_account(self, username, password):
        return self.Login(username, password)

    def list_accounts(self, user_id, session_token, wildcard):
        return self.ListAccounts(user_id, session_token, wildcard)

    def display_conversation(self, user_id, session_token, conversant_id):
        return self.DisplayConversation(user_id, session_token, conversant_id)
    
    def send_message(self, sender_user_id, session_token, recipient_user_id, message_content):
        return self.SendMessage(sender_user_id, session_token, recipient_user_id, message_content)

    def read_messages(self, user_id, session_token, number_of_messages_req):
        return self.ReadMessages(user_id, session_token, number_of_messages_req)

    def delete_message(self, user_id, message_uid, session_token):
        return self.DeleteMessage(user_id, message_uid, session_token)
    
    def delete_account(self, user_id, session_token):
        return self.DeleteAccount(user_id, session_token)

    def get_unread_messages(self, user_id, session_token):
        return self.GetUnreadMessages(user_id, session_token)

    def get_message_info(self, user_id, session_token, message_uid):
        # Get a 4-tuple from GetMessageInformation
        read_flag, sender_id, content_length, message_content = self.GetMessageInformation(user_id, session_token, message_uid)
    
        # Return only the 3 elements the GUI expects
        return (read_flag, sender_id, message_content)
    
    def get_username_by_id(self, user_id):
        return self.GetUsernameByID(user_id)

    def mark_message_as_read(self, user_id, session_token, message_uid):
        return self.MarkMessageAsRead(user_id, session_token, message_uid)
    
    def get_user_by_username(self, username):
        return self.GetUserByUsername(username)

    def hash_password(self, password: str):
        return hashlib.sha256(password.encode()).hexdigest()
        

if __name__ == "__main__":
    # Simple usage example:
    client = Client()
    try:
        if client.connect():
            # 1) CreateAccount example
            token_hex = client.CreateAccount("alice", "password123")
            print(f"CreateAccount => session token = {token_hex}")

            # 2) Login example
            success, token, unread_count = client.Login("alice", "password123")
            print(f"Login => success={success}, token={token}, unread_count={unread_count}")

            # 3) ListAccounts example
            if success:
                # Suppose user_id=1 is "alice" after creation
                # or you might do a GetUserByUsername to find it
                usernames = client.ListAccounts(
                    user_id=1,
                    session_token=token,
                    wildcard="a"
                )
                print(f"ListAccounts => {usernames}")
        else:
            print("[CLIENT] Could not connect to gRPC server.")
    finally:
        client.disconnect()
