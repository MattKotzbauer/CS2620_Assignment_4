import re
from typing import Optional, List, TypeVar, Generic, Union, Tuple

T = TypeVar('T')

class TSTNode(Generic[T]):
    def __init__(self, char: str):
        self.char = char
        self.left: Optional[TSTNode[T]] = None
        self.eq: Optional[TSTNode[T]] = None
        self.right: Optional[TSTNode[T]] = None
        self.is_end = False
        self.value: Optional[T] = None

class TernarySearchTree(Generic[T]):  # Key fix: make the class Generic[T]
    def __init__(self):
        self.root: Optional[TSTNode[T]] = None

    def add(self, word: str, value: Optional[T] = None) -> None:
        """Add a word to the TST, optionally with a value."""
        if not word:
            return
        self.root = self._add(self.root, word, value, 0)

    def _add(self, node: Optional[TSTNode[T]], word: str, value: Optional[T], index: int) -> TSTNode[T]:
        char = word[index]
        if node is None:
            node = TSTNode[T](char)  # Note: Added [T] here
        
        if char < node.char:
            node.left = self._add(node.left, word, value, index)
        elif char > node.char:
            node.right = self._add(node.right, word, value, index)
        else:
            if index + 1 == len(word):
                node.is_end = True
                node.value = value
            else:
                node.eq = self._add(node.eq, word, value, index + 1)
        return node

    def get(self, word: str) -> Optional[T]:
        """Get the value associated with a word."""
        if not word:
            return None
        
        node = self.root
        index = 0
        
        while node is not None:
            char = word[index]
            if char < node.char:
                node = node.left
            elif char > node.char:
                node = node.right
            else:
                index += 1
                if index == len(word):
                    return node.value if node.is_end else None
                node = node.eq
        
        return None

    def delete(self, word: str) -> None:
        """Delete a word from the TST."""
        if not word:
            return
        self.root = self._delete(self.root, word, 0)

    def _delete(self, node: Optional[TSTNode[T]], word: str, index: int) -> Optional[TSTNode[T]]:
        if node is None:
            return None

        char = word[index]
        if char < node.char:
            node.left = self._delete(node.left, word, index)
        elif char > node.char:
            node.right = self._delete(node.right, word, index)
        else:
            if index + 1 == len(word):
                node.is_end = False
                node.value = None
            else:
                node.eq = self._delete(node.eq, word, index + 1)

        if not node.is_end and node.eq is None:
            if node.left is None and node.right is None:
                return None
        return node

    def regex_search(self, pattern: str, return_values: bool = False) -> Union[List[str], List[T]]:
        """
        Search for matches using wildcards (* and ?).
        If return_values is True, returns list of values, otherwise returns list of words.
        """
        regex_pattern = '^' + re.escape(pattern).replace(r'\*', '.*').replace(r'\?', '.') + '$'
        prog = re.compile(regex_pattern)
        
        results: List[Tuple[str, Optional[T]]] = []
        self._collect(self.root, "", results)
        
        if return_values:
            return [value for word, value in results if prog.match(word) and value is not None]
        else:
            return [word for word, _ in results if prog.match(word)]

    def _collect(self, node: Optional[TSTNode[T]], prefix: str, 
                result: List[Tuple[str, Optional[T]]]) -> None:
        """Collect all (word, value) pairs in the tree."""
        if node is None:
            return

        self._collect(node.left, prefix, result)

        new_prefix = prefix + node.char
        if node.is_end:
            result.append((new_prefix, node.value))

        self._collect(node.eq, new_prefix, result)
        self._collect(node.right, prefix, result)


if __name__ == "__main__":
    # Test with strings
    tst = TernarySearchTree[str]()
    accounts = ["alice", "allen", "bob", "bobby", "carol", "carly", "dave"]
    for account in accounts:
        tst.add(account)

    print("All accounts:")
    print(tst.regex_search("*"))

    print("\nAccounts matching pattern 'a?l*':")
    matches = tst.regex_search("a?l*")
    print(matches)

    print("\nDeleting account 'allen' ...")
    tst.delete("allen")
    print("Accounts after deletion:")
    print(tst.regex_search("*"))
