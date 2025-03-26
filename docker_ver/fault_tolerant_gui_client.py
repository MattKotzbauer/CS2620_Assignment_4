import hashlib
from typing import Optional, Tuple, List
from fault_tolerant_client import FaultTolerantClient

class FaultTolerantGUIClient(FaultTolerantClient):
    """
    Adapter class that provides the same interface as the original GUI client
    but uses the fault-tolerant client implementation underneath.
    """
    
    def __init__(self, cluster_config_path: str, max_retry_attempts: int = 3):
        """
        Initialize the fault-tolerant GUI client.
        
        Args:
            cluster_config_path: Path to the cluster configuration JSON file
            max_retry_attempts: Maximum number of retry attempts for operations
        """
        super().__init__(cluster_config_path, max_retry_attempts)
        self._connected = False

    def connect(self) -> bool:
        """
        Establish connections to the cluster.
        Returns True if connected to at least one node, False otherwise.
        """
        try:
            self._init_connections()
            return self._connected
        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            return False

    def disconnect(self):
        """
        Gracefully close all connections.
        """
        for channel in self.channels.values():
            channel.close()
        self.channels.clear()
        self.stubs.clear()
        self._connected = False

    # No need to override CreateAccount as it has the same interface

    def Login(self, username: str, password: str) -> Tuple[bool, str, int]:
        """
        Log into an existing account.
        
        Returns:
            Tuple[bool, str, int]: (success, session_token_hex, unread_count)
        """
        try:
            result = super().Login(username, password)
            return (True, result[0], result[1])  # Assuming FaultTolerantClient returns (token, unread_count)
        except Exception as e:
            print(f"[CLIENT] Login failed: {e}")
            return (False, "", 0)

    def ListAccounts(self, user_id: int, session_token: str, wildcard: str) -> List[str]:
        """
        List matching accounts.
        
        Returns:
            List[str]: A list of usernames.
        """
        return super().ListAccounts(user_id, session_token, wildcard)

    def DisplayConversation(self, user_id: int, session_token: str, conversant_id: int) -> List[Tuple[int, str, bool]]:
        """
        Display the conversation between user_id and conversant_id.
        
        Returns:
            List[Tuple[int, str, bool]]: List of (message_id, message_content, sender_flag)
        """
        return super().DisplayConversation(user_id, session_token, conversant_id)

    def SendMessage(self, sender_id: int, session_token: str, recipient_id: int, message: str) -> bool:
        """
        Send a message from sender to recipient.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            super().SendMessage(sender_id, session_token, recipient_id, message)
            return True
        except Exception as e:
            print(f"[CLIENT] SendMessage failed: {e}")
            return False

    def ReadMessages(self, user_id: int, session_token: str, num_messages: int) -> bool:
        """
        Read a specified number of messages.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            super().ReadMessages(user_id, session_token, num_messages)
            return True
        except Exception as e:
            print(f"[CLIENT] ReadMessages failed: {e}")
            return False

    def DeleteMessage(self, user_id: int, message_id: int, session_token: str) -> bool:
        """
        Delete a specific message.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            super().DeleteMessage(user_id, message_id, session_token)
            return True
        except Exception as e:
            print(f"[CLIENT] DeleteMessage failed: {e}")
            return False

    def DeleteAccount(self, user_id: int, session_token: str) -> bool:
        """
        Delete the user's account.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            super().DeleteAccount(user_id, session_token)
            return True
        except Exception as e:
            print(f"[CLIENT] DeleteAccount failed: {e}")
            return False

    def GetUnreadMessages(self, user_id: int, session_token: str) -> List[Tuple[int, int, int]]:
        """
        Get unread messages for the user.
        
        Returns:
            List[Tuple[int, int, int]]: List of (message_id, sender_id, receiver_id)
        """
        return super().GetUnreadMessages(user_id, session_token)

    def GetMessageInformation(self, user_id: int, session_token: str, message_id: int) -> Tuple[bool, int, int, str]:
        """
        Get information about a specific message.
        
        Returns:
            Tuple[bool, int, int, str]: (read_flag, sender_id, content_length, message_content)
        """
        return super().GetMessageInformation(user_id, session_token, message_id)

    def GetUsernameByID(self, user_id: int) -> str:
        """
        Get username for a given user ID.
        
        Returns:
            str: Username associated with the ID
        """
        return super().GetUsernameByID(user_id)

    def MarkMessageAsRead(self, user_id: int, session_token: str, message_id: int) -> bool:
        """
        Mark a message as read.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            super().MarkMessageAsRead(user_id, session_token, message_id)
            return True
        except Exception as e:
            print(f"[CLIENT] MarkMessageAsRead failed: {e}")
            return False

    def GetUserByUsername(self, username: str) -> Tuple[bool, int]:
        """
        Get user ID for a given username.
        
        Returns:
            Tuple[bool, int]: (found_status, user_id)
        """
        return super().GetUserByUsername(username)
