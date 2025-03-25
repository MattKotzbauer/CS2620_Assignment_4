from typing import Dict, List, Tuple, Optional, Set, Union
from collections import defaultdict
from core_entities import User, Message
# from tst_implementation import TernarySearchTree


class GlobalUserBase:
    """
    Maps user IDs to User instances. Provides the primary storage for user data
    and manages user ID generation.
    """
    def __init__(self):
        self.users: Dict[int, User] = {}
        self._next_user_id: int = 1
        self._deleted_user_ids: Set[int] = set()

# class GlobalUserTrie:
    # """
    # Maintains a Ternary Search Tree for username lookups, supporting pattern matching
    # with wildcards (* for any sequence, ? for any character).
    # """
    # def __init__(self):
        # self.trie: TernarySearchTree[User] = TernarySearchTree[User]()
class GlobalUserTrie:
    def __init__(self):
        self.store = {}
    
    def add(self, word: str, value: User):
        self.store[word] = value
    
    def get(self, word: str) -> Optional[User]:
        return self.store.get(word)
    
    def regex_search(self, pattern: str, return_values: bool = False) -> List[Union[str, User]]:
        # Very basic search for debugging purposes
        results = []
        for key, value in self.store.items():
            if re.fullmatch(pattern.replace("*", ".*").replace("?", "."), key):
                results.append(value if return_values else key)
        return results


        
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

        
