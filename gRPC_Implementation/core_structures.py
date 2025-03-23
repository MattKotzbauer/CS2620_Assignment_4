from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from core_entities import User, Message
from tst_implementation import TernarySearchTree

class GlobalUserBase:
    """
    Maps user IDs to User instances. Provides the primary storage for user data
    and manages user ID generation.
    """
    def __init__(self):
        self.users: Dict[int, User] = {}
        self._next_user_id: int = 1
        self._deleted_user_ids: Set[int] = set()

class GlobalUserTrie:
    """
    Maintains a Ternary Search Tree for username lookups, supporting pattern matching
    with wildcards (* for any sequence, ? for any character).
    """
    def __init__(self):
        self.trie: TernarySearchTree[User] = TernarySearchTree[User]()

# (this guy is a massive todo)
class GlobalSessionTokens:
    """
    Maps user IDs to their current session tokens. Handles token management
    for active user sessions.
    """
    def __init__(self):
        self.tokens: Dict[int, str] = {}

class GlobalMessageBase:
    """
    Maps message UIDs to Message instances. Provides the primary storage for
    message data and manages message ID generation.
    """
    def __init__(self):
        self.messages: Dict[int, Message] = {}
        self._next_message_id = 1
        self._deleted_message_ids: Set[int] = set()

class GlobalConversations:
    """
    Maps user ID pairs to lists of messages between those users. Maintains
    the conversation history between any two users.
    """
    def __init__(self):
        self.conversations: Dict[Tuple[int, int], List[Message]] = defaultdict(list)

        
