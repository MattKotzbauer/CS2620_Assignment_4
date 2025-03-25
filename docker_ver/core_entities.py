

"""
NOTES:
* code for Message, User entities
* all classes are going to be initialized system-side
   * Users will be initialized once server receives (and checks for non-conflicting) account creation packet
   * Messages will be initialized as soon as system receives them from sender client
"""

import time
import hashlib
from collections import deque

class Message:
    """
    Represents a single message between users.
    
    Attributes:
        uid (int): Unique identifier for the message
        contents (str): The actual message text
        sender_id (int): User ID of the sender
        receiver_id (int): User ID of the receiver
        has_been_read (bool): Whether the message has been read
        timestamp (int): Unix timestamp of when the message was sent
    """
    def __init__(self, uid: int, contents: str, sender_id: int, receiver_id: int, 
                 has_been_read: bool = False, timestamp: int = None):
        self.uid = uid
        self.contents = contents
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.has_been_read = has_been_read
        self.timestamp = timestamp if timestamp is not None else int(time.time())

class User:
    """
    Represents a user in the messaging system.
    
    Attributes:
        user_id (int): Unique identifier for the user
        username (str): User's chosen username
        password_hash (str): SHA-256 hash of the user's password
        unread_messages (deque): Queue of unread message UIDs
        recent_conversants (list): List of recent user IDs ordered by message recency
    """
    def __init__(self, userID: int, username: str, passwordHash: str):
        self.userID = userID
        self.username = username
        self.passwordHash = passwordHash
        self.unread_messages = deque()
        self.recent_conversants = []

    def add_unread_message(self, message_uid: int):
        """Add a message UID to the unread messages queue."""
        self.unread_messages.append(message_uid)
    
    def mark_message_read(self, message_uid: int) -> bool:
        """
        Mark a message as read and remove it from the unread queue.
        Returns True if the message was found and marked as read.
        """
        try:
            self.unread_messages.remove(message_uid)
            return True
        except ValueError:
            return False
    
    def update_recent_conversant(self, user_id: int):
        """
        Update the recent conversants list.
        Moves the given user_id to the front if it exists, otherwise adds it.
        """
        if user_id in self.recent_conversants:
            self.recent_conversants.remove(user_id)
        self.recent_conversants.insert(0, user_id)

