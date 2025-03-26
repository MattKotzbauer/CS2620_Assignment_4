# fault_tolerant_client.py
import grpc
import hashlib
import time
import json
import random
import logging
import sys
from typing import Optional, Tuple, List, Dict, Any

# Protobuf-generated modules
import exp_pb2
import exp_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("client.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FaultTolerantClient:
    """
    A fault-tolerant client implementation that can handle server failures
    by reconnecting to other servers in the cluster.
    """

    def __init__(self, cluster_config_path: str, max_retry_attempts: int = 3):
        """
        Initialize the client with a cluster configuration.
        
        Args:
            cluster_config_path: Path to the JSON file containing the cluster configuration
            max_retry_attempts: Maximum number of retry attempts when an operation fails
        """
        self.max_retry_attempts = max_retry_attempts
        self.channels = {}  # Maps node_id to grpc.Channel
        self.stubs = {}     # Maps node_id to MessagingServiceStub
        self.leader_id = None
        self._connected = False
        self.dead_nodes = {} # Maps node_id to timestamp of last failure
        self.dead_timeout = 3 # Seconds to wait before retrying a dead node
        
        
        # Load cluster configuration
        with open(cluster_config_path, 'r') as f:
            self.cluster_config = json.load(f)
        
        # Initialize connections to all servers
        self._init_connections()
    
    def _init_connections(self):
        """Initialize gRPC connections to all servers in the cluster."""
        for node_id, address in self.cluster_config.items():
            try:
                channel = grpc.insecure_channel(address)
                self.channels[node_id] = channel
                self.stubs[node_id] = exp_pb2_grpc.MessagingServiceStub(channel)
                logger.info(f"Initialized connection to node {node_id} at {address}")
            except Exception as e:
                logger.warning(f"Failed to initialize connection to node {node_id}: {str(e)}")
        
        # Try to identify the leader
        self._find_leader()

    def _find_leader(self) -> bool:
        # Try for a fixed number of attempts
        for attempt in range(10):
            logger.info(f"Attempt {attempt+1}: available stubs: {list(self.stubs.keys())}")
            for node_id, stub in self.stubs.items():
                try:
                    request = exp_pb2.LeaderPingRequest()
                    stub.LeaderPing(request, timeout=5.0)
                    self.leader_id = node_id
                    logger.info(f"Found leader: node {node_id}")
                    self._connected = True
                    return True
                except grpc.RpcError as e:
                    details = e.details() or ""
                    logger.info(f"LeaderPing failed for node {node_id}: {e.code()} - {details}")
                    if "Not the leader. Try " in details:
                        new_addr = details.split("Try ")[1].strip()
                        for possible_id, address in self.cluster_config.items():
                            if address == new_addr:
                                self.leader_id = possible_id
                                logger.info(f"Found leader via redirect: node {possible_id}")
                                self._connected = True
                                return True
            logger.warning("Leader not found. Waiting for leader election to complete...")
            time.sleep(2)
        self._connected = False
        return False

        
    """
    def _find_leader(self) -> bool:
        
        for node_id, stub in self.stubs.items():
            try:
                request = exp_pb2.LeaderPingRequest()
                stub.LeaderPing(request, timeout=10.0)
                # If we got here without an exception, node_id is leader
                self.leader_id = node_id
                logger.info(f"Found leader: node {node_id}")
                self._connected = True
                return True

            except grpc.RpcError as e:
                details = e.details() or ""
                # If "Not the leader" appears, we see if it gave us a redirect
                if "Not the leader. Try " in details:
                    new_addr = details.split("Try ")[1].strip()
                    # Now we can see if that maps to some node_id in cluster_config
                    for possible_id, address in self.cluster_config.items():
                        if address == new_addr:
                            self.leader_id = possible_id
                            logger.info(f"Found leader via redirect: node {possible_id}")
                            self._connected = True
                            return True
            # Otherwise, keep trying the next node

        logger.warning("Failed to identify a leader in the cluster via LeaderPing")
        self._connected = False
        return False
        """

    def _ensure_connected(self):
        current_time = time.time()
        # Try to refresh connections for nodes missing from stubs,
        # but only for nodes that are not in dead_nodes or where the timeout expired.
        for node_id, address in self.cluster_config.items():
            if node_id not in self.stubs:
                if node_id in self.dead_nodes and (current_time - self.dead_nodes[node_id] < self.dead_timeout):
                    continue  # Skip reinitialization for recently dead nodes.
                try:
                    channel = grpc.insecure_channel(address)
                    self.channels[node_id] = channel
                    self.stubs[node_id] = exp_pb2_grpc.MessagingServiceStub(channel)
                    logger.info(f"Reinitialized connection to node {node_id} at {address}")
                    if node_id in self.dead_nodes:
                        del self.dead_nodes[node_id]
                except Exception as e:
                    logger.warning(f"Failed to reinitialize connection to node {node_id}: {str(e)}")
                    self.dead_nodes[node_id] = current_time

        if not self._find_leader():
            raise ConnectionError("Could not connect to any server in the cluster")


    def _execute_with_retry(self, operation, *args, **kwargs):
        attempt = 0
        last_error = None

        while attempt < self.max_retry_attempts:
            try:
                self._ensure_connected()
                return operation(*args, **kwargs)
            except grpc.RpcError as e:
                details = e.details() or ""
                code = e.code()
                logger.info(f"_execute_with_retry: caught RpcError code={code}, details={details}")

                # If the error indicates the server is unreachable, remove that node's stub.
                if code in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
                    # If the current leader is unreachable, remove it from the pool
                    if self.leader_id and self.leader_id in self.stubs:
                        logger.info(f"Marking unreachable leader {self.leader_id} as dead")
                        self.dead_nodes[self.leader_id] = time.time()
                        del self.stubs[self.leader_id]
                        self.leader_id = None
                    else:
                        # Otherwise, remove any stub that errors out
                        for node_id in list(self.stubs.keys()):
                            try:
                                # Optionally, you could perform a quick health-check here
                                logger.info(f"Marking unreachable node {node_id} as dead")
                                self.dead_nodes[node_id] = time.time()
                                del self.stubs[node_id]
                                logger.info(f"Removed unreachable node {node_id} from stubs")
                            except Exception:
                                pass
                    attempt += 1
                else:
                    attempt += 1
                    last_error = e
                    
                time.sleep(0.1 * (2 ** attempt))

        if last_error:
            raise last_error
        raise ConnectionError("Failed to execute operation after multiple retries")

    
    def CreateAccount(self, username: str, password: str) -> str:
        """
        Create a new account.

        Args:
            username (str): The username for the new account
            password (str): The password for the new account

        Returns:
            str: The 32-byte session token in hex.
        """
        def operation():
            # Hash password -> 32 bytes
            hashed_password = hashlib.sha256(password.encode()).digest()
            
            request = exp_pb2.CreateAccountRequest(
                username=username,
                password_hash=hashed_password
            )
            
            # Use the leader stub if available
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                # If no leader is known, use a random stub
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            response = stub.CreateAccount(request)
            return response.session_token.hex()
        
        return self._execute_with_retry(operation)
    
    def Login(self, username: str, password: str) -> Tuple[bool, str, int]:
        """
        Log into an existing account.

        Args:
            username (str): The username
            password (str): The password

        Returns:
            Tuple[bool, str, int]: (success, session_token_hex, unread_count)
        """
        def operation():
            hashed_password = hashlib.sha256(password.encode()).digest()
            
            request = exp_pb2.LoginRequest(
                username=username,
                password_hash=hashed_password
            )
            
            # Use the leader stub if available
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                # If no leader is known, use a random stub
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            response = stub.Login(request)
            success = (response.status == exp_pb2.STATUS_SUCCESS)
            token_hex = response.session_token.hex()
            unread_count = response.unread_count
            return (success, token_hex, unread_count)
        
        return self._execute_with_retry(operation)
    
    def ListAccounts(self, user_id: int, session_token: str, wildcard: str) -> List[str]:
        """
        List matching accounts.

        Args:
            user_id (int): The user ID
            session_token (str): The session token
            wildcard (str): Wildcard pattern for matching usernames

        Returns:
            List[str]: A list of usernames
        """
        def operation():
            token_bytes = bytes.fromhex(session_token)
            
            request = exp_pb2.ListAccountsRequest(
                user_id=user_id,
                session_token=token_bytes,
                wildcard=wildcard
            )
            
            # This operation can be performed on any node, not just the leader
            # We'll still start with the leader for consistency
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            response = stub.ListAccounts(request)
            return list(response.usernames)
        
        return self._execute_with_retry(operation)
    
    def DisplayConversation(self, user_id: int, session_token: str, conversant_id: int) -> List[Tuple[int, str, bool]]:
        """
        Display the conversation between user_id and conversant_id.

        Args:
            user_id (int): The user ID
            session_token (str): The session token
            conversant_id (int): The ID of the user to converse with

        Returns:
            A list of tuples (message_id, message_content, sender_flag).
            sender_flag = True if the user was the sender, False otherwise.
        """
        def operation():
            token_bytes = bytes.fromhex(session_token)
            
            request = exp_pb2.DisplayConversationRequest(
                user_id=user_id,
                session_token=token_bytes,
                conversant_id=conversant_id
            )
            
            # This operation can be performed on any node
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            response = stub.DisplayConversation(request)
            
            # Convert repeated ConversationMessage -> list of (msg_id, content, is_sender)
            result = []
            for msg in response.messages:
                result.append((msg.message_id, msg.content, msg.sender_flag))
            return result
        
        return self._execute_with_retry(operation)

    """
    def SendMessage(self, sender_user_id: int, session_token: str, recipient_user_id: int, message_content: str) -> bool:
        def operation():
            token_bytes = bytes.fromhex(session_token)
            
            request = exp_pb2.SendMessageRequest(
                sender_user_id=sender_user_id,
                session_token=token_bytes,
                recipient_user_id=recipient_user_id,
                message_content=message_content
            )
            
            # This must be sent to the leader
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                # If no leader is known, try a random server
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            try:
                stub.SendMessage(request)
                return True
            except grpc.RpcError as e:
                # Check if the error is due to not being the leader
                if "Not the leader" in e.details() if hasattr(e, 'details') else "":
                    # Find the real leader and try again
                    self._find_leader()
                    if self.leader_id:
                        stub = self.stubs[self.leader_id]
                        stub.SendMessage(request)
                        return True
                    else:
                        return False
                else:
                    logger.error(f"Failed to send message: {e}")
                    return False
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                return False
        
        return self._execute_with_retry(operation)

    """
    def SendMessage(self, sender_user_id: int, session_token: str, recipient_user_id: int, message_content: str) -> bool:
        def operation():
            token_bytes = bytes.fromhex(session_token)
            request = exp_pb2.SendMessageRequest(
                sender_user_id=sender_user_id,
                session_token=token_bytes,
                recipient_user_id=recipient_user_id,
                message_content=message_content
            )
            # Prefer the leader's stub if available, else pick one at random.
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                stub = random.choice(list(self.stubs.values()))

            # Try sending the message. Any error here will be retried.
            stub.SendMessage(request)
            return True

        return self._execute_with_retry(operation)

    
    def ReadMessages(self, user_id: int, session_token: str, number_of_messages_req: int) -> bool:
        """
        Read/acknowledge a number of messages.

        Args:
            user_id (int): User ID
            session_token (str): Session token
            number_of_messages_req (int): Number of messages to mark as read

        Returns:
            bool: True if successful, False otherwise
        """
        def operation():
            token_bytes = bytes.fromhex(session_token)

            request = exp_pb2.ReadMessagesRequest(
                user_id=user_id,
                session_token=token_bytes,
                number_of_messages_req=number_of_messages_req
            )
            
            # This must be sent to the leader
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            try:
                stub.ReadMessages(request)
                return True
            except Exception as e:
                logger.error(f"Failed to read messages: {e}")
                return False
        
        return self._execute_with_retry(operation)
    
    def DeleteMessage(self, user_id: int, message_uid: int, session_token: str) -> bool:
        """
        Delete a specific message.

        Args:
            user_id (int): User ID
            message_uid (int): Message unique ID
            session_token (str): Session token

        Returns:
            bool: True if successful, False otherwise
        """
        def operation():
            token_bytes = bytes.fromhex(session_token)

            request = exp_pb2.DeleteMessageRequest(
                user_id=user_id,
                message_uid=message_uid,
                session_token=token_bytes
            )
            
            # This must be sent to the leader
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            try:
                stub.DeleteMessage(request)
                return True
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
                return False
        
        return self._execute_with_retry(operation)
    
    def DeleteAccount(self, user_id: int, session_token: str) -> bool:
        """
        Delete the specified account.

        Args:
            user_id (int): User ID
            session_token (str): Session token

        Returns:
            bool: True if successful, False otherwise
        """
        def operation():
            token_bytes = bytes.fromhex(session_token)

            request = exp_pb2.DeleteAccountRequest(
                user_id=user_id,
                session_token=token_bytes
            )
            
            # This must be sent to the leader
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            try:
                stub.DeleteAccount(request)
                return True
            except Exception as e:
                logger.error(f"Failed to delete account: {e}")
                return False
        
        return self._execute_with_retry(operation)
    
    def GetUnreadMessages(self, user_id: int, session_token: str) -> List[Tuple[int, int, int]]:
        """
        Fetch unread messages for a user.

        Args:
            user_id (int): User ID
            session_token (str): Session token

        Returns:
            List[Tuple[int, int, int]]: List of (message_uid, sender_id, receiver_id)
        """
        def operation():
            token_bytes = bytes.fromhex(session_token)

            request = exp_pb2.GetUnreadMessagesRequest(
                user_id=user_id,
                session_token=token_bytes
            )
            
            # This can be performed on any node
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            resp = stub.GetUnreadMessages(request)

            results = []
            for m in resp.messages:
                results.append((m.message_uid, m.sender_id, m.receiver_id))
            return results
        
        return self._execute_with_retry(operation)
    
    def GetMessageInformation(self, user_id: int, session_token: str, message_uid: int) -> Tuple[bool, int, int, str]:
        """
        Get message info (read status, sender ID, content length, content).

        Args:
            user_id (int): User ID
            session_token (str): Session token
            message_uid (int): Message unique ID

        Returns:
            Tuple[bool, int, int, str]: (read_flag, sender_id, content_length, message_content)
        """
        def operation():
            token_bytes = bytes.fromhex(session_token)

            request = exp_pb2.GetMessageInformationRequest(
                user_id=user_id,
                session_token=token_bytes,
                message_uid=message_uid
            )
            
            # This can be performed on any node
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            resp = stub.GetMessageInformation(request)
            return (resp.read_flag, resp.sender_id, resp.content_length, resp.message_content)
        
        return self._execute_with_retry(operation)
    
    def GetUsernameByID(self, user_id: int) -> str:
        """
        Get username from a user ID.

        Args:
            user_id (int): User ID

        Returns:
            str: The username, or empty string if not found
        """
        def operation():
            request = exp_pb2.GetUsernameByIDRequest(user_id=user_id)
            
            # This can be performed on any node
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            resp = stub.GetUsernameByID(request)
            return resp.username
        
        return self._execute_with_retry(operation)
    
    def MarkMessageAsRead(self, user_id: int, session_token: str, message_uid: int) -> bool:
        """
        Mark the specified message as read.

        Args:
            user_id (int): User ID
            session_token (str): Session token
            message_uid (int): Message unique ID

        Returns:
            bool: True if successful, False otherwise
        """
        def operation():
            token_bytes = bytes.fromhex(session_token)

            request = exp_pb2.MarkMessageAsReadRequest(
                user_id=user_id,
                session_token=token_bytes,
                message_uid=message_uid
            )
            
            # This must be sent to the leader
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            try:
                stub.MarkMessageAsRead(request)
                return True
            except Exception as e:
                logger.error(f"Failed to mark message as read: {e}")
                return False
        
        return self._execute_with_retry(operation)
    
    def GetUserByUsername(self, username: str) -> Tuple[bool, Optional[int]]:
        """
        Retrieve a user by username.

        Args:
            username (str): Username to look up

        Returns:
            Tuple[bool, Optional[int]]: (found, user_id) tuple
        """
        def operation():
            request = exp_pb2.GetUserByUsernameRequest(username=username)
            
            # This can be performed on any node
            if self.leader_id and self.leader_id in self.stubs:
                stub = self.stubs[self.leader_id]
            else:
                node_id = random.choice(list(self.stubs.keys()))
                stub = self.stubs[node_id]
            
            resp = stub.GetUserByUsername(request)

            if resp.status == exp_pb2.FOUND:
                return (True, resp.user_id)
            else:
                return (False, None)
        
        return self._execute_with_retry(operation)
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def disconnect(self):
        """Close all gRPC channels."""
        for channel in self.channels.values():
            channel.close()
        self.channels.clear()
        self.stubs.clear()
        self._connected = False
        self.leader_id = None

    # Wrapper methods for compatibility with the original client interface
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


# Main execution section for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Chat client')
    parser.add_argument('--config', default='cluster_config.json', help='Path to cluster configuration file')
    args = parser.parse_args()
    
    try:
        # Create and test the client
        client = FaultTolerantClient(args.config)
        
        # Basic connectivity test
        print("Testing cluster connectivity...")
        if client._find_leader():
            print(f"Successfully connected to cluster. Current leader: {client.leader_id}")
        else:
            print("Failed to connect to cluster or find a leader.")
            sys.exit(1)
        
        # Try creating an account
        username = f"test_user_{int(time.time())}"
        password = "test_password"
        
        try:
            print(f"Creating test account: {username}")
            token = client.create_account(username, password)
            print(f"Account created successfully! Token: {token[:10]}...")
            
            # Try logging in
            print(f"Testing login with {username}")
            success, token, unread_count = client.log_into_account(username, password)
            if success:
                print(f"Login successful! Token: {token[:10]}..., Unread messages: {unread_count}")
                
                # Get user ID
                found, user_id = client.get_user_by_username(username)
                if found:
                    print(f"Retrieved user ID: {user_id}")
                    
                    # List accounts
                    print("Listing accounts matching 'test*'")
                    accounts = client.list_accounts(user_id, token, "test*")
                    print(f"Found {len(accounts)} matching accounts: {accounts}")
                    
                    # Clean up - delete the test account
                    print(f"Deleting test account {username}")
                    if client.delete_account(user_id, token):
                        print("Account deleted successfully")
                    else:
                        print("Failed to delete account")
                else:
                    print("Failed to retrieve user ID")
            else:
                print("Login failed")
                
        except Exception as e:
            print(f"Error during testing: {str(e)}")
        
        # Disconnect the client
        client.disconnect()
        print("Client disconnected.")
        
    except Exception as e:
        print(f"Error initializing client: {str(e)}")
        sys.exit(1)
