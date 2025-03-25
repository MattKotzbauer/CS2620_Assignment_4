# raft_node.py
import os
import sys
import time
import json
import random
import threading
import sqlite3
import grpc
import hashlib
from concurrent import futures
from typing import Dict, List, Optional, Tuple, Set, Any
from collections import deque
import logging

# Existing imports
import exp_pb2
import exp_pb2_grpc
from core_entities import User, Message
from core_structures import GlobalUserBase, GlobalUserTrie, GlobalSessionTokens, GlobalMessageBase, GlobalConversations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("raft_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define Raft node states
class NodeState:
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
    LEADER = "LEADER"

class RaftNode(exp_pb2_grpc.RaftServiceServicer):
    """Implementation of a Raft consensus node for the chat system."""
    
    def __init__(self, node_id: str, cluster_config: Dict[str, str], data_dir: str):
        """
        Initialize a Raft node.
        
        Args:
            node_id: Unique identifier for this node
            cluster_config: Dict mapping node_ids to "host:port" addresses
            data_dir: Directory to store persistent data
        """
        self.node_id = node_id
        self.cluster_config = cluster_config
        self.address = cluster_config[node_id]
        self.data_dir = data_dir
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize Raft state
        self.state = NodeState.FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.leader_id = None
        
        # Log entries and commit index
        self.log = []  # List of (term, command) entries
        self.commit_index = -1
        self.last_applied = -1
        
        # Leader state (initialized when becoming leader)
        self.next_index = {}  # Dict mapping node_id to next log index
        self.match_index = {}  # Dict mapping node_id to highest log index known to be replicated
        
        # Timing variables
        self.election_timeout = self._generate_election_timeout()
        self.last_heartbeat = time.time()
        
        # Initialize database connection
        self.db_path = os.path.join(data_dir, f"node_{node_id}.db")
        self._init_database()
        
        # Initialize in-memory state (loaded from persistent storage)
        self.user_base = GlobalUserBase()
        self.user_trie = GlobalUserTrie()
        self.session_tokens = GlobalSessionTokens()
        self.message_base = GlobalMessageBase()
        self.conversations = GlobalConversations()
        
        # Load state from database
        self._load_state_from_db()
        
        # Initialize peers (gRPC connections to other nodes)
        self.peers = {}
        self._init_peer_connections()
        
        # Start background threads
        self.running = True
        self.raft_thread = threading.Thread(target=self._run_raft_loop)
        self.raft_thread.daemon = True
        self.raft_thread.start()
        
        logger.info(f"Initialized Raft node {self.node_id} at {self.address}")
    
    def _init_database(self):
        """Initialize the SQLite database for persistent storage."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create tables if they don't exist
        
        # Raft state table
        c.execute('''
        CREATE TABLE IF NOT EXISTS raft_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        # Log entries table
        # c.execute('''
        # CREATE TABLE IF NOT EXISTS log_entries (
            # index INTEGER PRIMARY KEY,
            # term INTEGER,
            # command TEXT
        # )
        # ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS log_entries (
        log_index INTEGER PRIMARY KEY,
        term INTEGER,
        command TEXT
        )
        ''')
        
        # Users table
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            data TEXT
        )
        ''')
        
        # Messages table
        c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY,
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT,
            has_been_read INTEGER,
            timestamp INTEGER
        )
        ''')
        
        # Session tokens table
        c.execute('''
        CREATE TABLE IF NOT EXISTS session_tokens (
            user_id INTEGER PRIMARY KEY,
            token TEXT,
            expiry INTEGER
        )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def _load_state_from_db(self):
        """Load the node's state from the database."""

        print(f"Loaded {len(self.user_base.users)} users and {len(self.message_base.messages)} messages from DB")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Load Raft state
        c.execute("SELECT key, value FROM raft_state")
        raft_state = dict(c.fetchall())
        
        if "current_term" in raft_state:
            self.current_term = int(raft_state["current_term"])
        if "voted_for" in raft_state:
            self.voted_for = raft_state["voted_for"] if raft_state["voted_for"] != "None" else None
        if "commit_index" in raft_state:
            self.commit_index = int(raft_state["commit_index"])
        
        # Load log entries
        c.execute("SELECT term, command FROM log_entries ORDER BY log_index ASC")
        self.log = [(term, json.loads(command)) for term, command in c.fetchall()]
        
        # Load users
        c.execute("SELECT user_id, username, password_hash, data FROM users")
        for user_id, username, password_hash, data in c.fetchall():
            print(f"Loading user from DB: {user_id}, {username}, data: {data}")

            user_data = json.loads(data)
            user = User(user_id, username, password_hash)
            user.unread_messages = deque(user_data.get("unread_messages", []))
            user.recent_conversants = user_data.get("recent_conversants", [])
            
            self.user_base.users[user_id] = user
            self.user_trie.add(username, user)
        print(f"Loaded state: {len(self.user_base.users)} users, {len(self.message_base.messages)} messages")

            
        # Load messages
        c.execute("SELECT message_id, sender_id, receiver_id, content, has_been_read, timestamp FROM messages")
        for msg_id, sender_id, receiver_id, content, has_been_read, timestamp in c.fetchall():
            message = Message(
                msg_id, 
                content, 
                sender_id, 
                receiver_id,
                bool(has_been_read),
                timestamp
            )
            self.message_base.messages[msg_id] = message
            
            # Update conversation
            conversation_key = tuple(sorted([sender_id, receiver_id]))
            self.conversations.conversations[conversation_key].append(message)
        
        # Load session tokens
        c.execute("SELECT user_id, token, expiry FROM session_tokens WHERE expiry > ?", (int(time.time()),))
        for user_id, token, expiry in c.fetchall():
            self.session_tokens.tokens[user_id] = token
        
        conn.close()
        
        # Update next_user_id and next_message_id based on existing data
        if self.user_base.users:
            self.user_base._next_user_id = max(self.user_base.users.keys()) + 1
        if self.message_base.messages:
            self.message_base._next_message_id = max(self.message_base.messages.keys()) + 1
        
        logger.info(f"Loaded state from database: {len(self.user_base.users)} users, {len(self.message_base.messages)} messages")
    
    def _persist_raft_state(self):
        """Persist Raft state to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("DELETE FROM raft_state")
        c.execute("INSERT INTO raft_state VALUES (?, ?)", ("current_term", str(self.current_term)))
        c.execute("INSERT INTO raft_state VALUES (?, ?)", ("voted_for", str(self.voted_for)))
        c.execute("INSERT INTO raft_state VALUES (?, ?)", ("commit_index", str(self.commit_index)))
        
        conn.commit()
        conn.close()
    
    def _persist_log_entry(self, index: int, term: int, command: Dict):
        """Persist a log entry to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("INSERT OR REPLACE INTO log_entries VALUES (?, ?, ?)",
                 (index, term, json.dumps(command)))
        
        conn.commit()
        conn.close()
    
    def _persist_user(self, user: User):
        """Persist a user to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Serialize user data
        user_data = {
            "unread_messages": list(user.unread_messages),
            "recent_conversants": user.recent_conversants
        }
        print(f"Persisting user: {user.userID}, {user.username}, {user_data}")
        
        c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
                 (user.userID, user.username, user.passwordHash, json.dumps(user_data)))
        
        conn.commit()
        conn.close()
    
    def _persist_message(self, message: Message):
        """Persist a message to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("INSERT OR REPLACE INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                 (message.uid, message.sender_id, message.receiver_id, 
                  message.contents, int(message.has_been_read), message.timestamp))
        
        conn.commit()
        conn.close()
    
    def _persist_session_token(self, user_id: int, token: str, expiry: int = None):
        """Persist a session token to the database."""
        if expiry is None:
            # Default expiry: 1 day
            expiry = int(time.time()) + 86400
            
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("INSERT OR REPLACE INTO session_tokens VALUES (?, ?, ?)",
                 (user_id, token, expiry))
        
        conn.commit()
        conn.close()
    
    def _generate_election_timeout(self):
        """Generate a random election timeout between 150-300ms."""
        # return random.uniform(0.3, 0.6)  # in seconds for easier testing
        return random.uniform(10.0, 13.0)
    
    def _init_peer_connections(self):
        """Initialize gRPC connections to peer nodes."""
        print(f"[DEBUG] Node {self.node_id} initializing peer connections")
        for node_id, address in self.cluster_config.items():
            if node_id != self.node_id:
                try:
                    print(f"[DEBUG] Node {self.node_id} connecting to peer {node_id} at {address}")
                    channel = grpc.insecure_channel(address)
                    stub = exp_pb2_grpc.RaftServiceStub(channel)
                    self.peers[node_id] = stub
                    print(f"[DEBUG] Successfully created stub for {node_id}")
                except Exception as e:
                    print(f"[DEBUG] Error creating stub for {node_id}: {str(e)}")
                # channel = grpc.insecure_channel(address)
                # stub = exp_pb2_grpc.RaftServiceStub(channel)
                # self.peers[node_id] = stub
    
    def _run_raft_loop(self):
        """Main Raft algorithm loop."""
        while self.running:
            current_time = time.time()
            
            if self.state == NodeState.FOLLOWER:
                # Check if election timeout has elapsed
                if current_time - self.last_heartbeat > self.election_timeout:
                    self._become_candidate()
            
            elif self.state == NodeState.CANDIDATE:
                # Start election
                self._start_election()
            
            elif self.state == NodeState.LEADER:
                # Send heartbeats/AppendEntries
                self._send_heartbeats()
            
            # Apply committed entries to state machine
            self._apply_committed_entries()
            
            # Sleep briefly to avoid consuming too much CPU
            time.sleep(0.05)
    
    def _become_candidate(self):
        """Transition to candidate state and start an election."""
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.election_timeout = self._generate_election_timeout()
        self.last_heartbeat = time.time()
        
        self._persist_raft_state()
        
        logger.info(f"Node {self.node_id} became candidate for term {self.current_term}")
    
    def _start_election(self):
        """Start a leader election."""
        # Increment current term and vote for self
        votes_received = 1  # Vote for self
        
        # Request votes from all other nodes
        for peer_id, stub in self.peers.items():
            try:
                request = exp_pb2.RequestVoteRequest(
                    term=self.current_term,
                    candidate_id=self.node_id,
                    last_log_index=len(self.log) - 1,
                    last_log_term=self.log[-1][0] if self.log else 0
                )
                
                response = stub.RequestVote(request, timeout=10)
                
                if response.vote_granted:
                    votes_received += 1
                
                # If we discover a higher term, revert to follower
                if response.term > self.current_term:
                    self.current_term = response.term
                    self.state = NodeState.FOLLOWER
                    self.voted_for = None
                    self._persist_raft_state()
                    logger.info(f"Node {self.node_id} reverted to follower (higher term)")
                    return
                
            except Exception as e:
                logger.warning(f"Failed to request vote from {peer_id}: {str(e)}")
        
        # Check if we've received a majority of votes
        if votes_received > len(self.cluster_config) / 2:
            self._become_leader()
    
    def _become_leader(self):
        """Transition to leader state."""
        self.state = NodeState.LEADER
        self.leader_id = self.node_id
        
        # Initialize leader state
        self.next_index = {node_id: len(self.log) for node_id in self.cluster_config if node_id != self.node_id}
        self.match_index = {node_id: -1 for node_id in self.cluster_config if node_id != self.node_id}
        
        logger.info(f"Node {self.node_id} became leader for term {self.current_term}")
        
        # Send immediate heartbeats
        self._send_heartbeats()
    
    def _send_heartbeats(self):
        """Send AppendEntries RPCs to all peers (as heartbeats or to replicate logs)."""
        for peer_id, stub in self.peers.items():
            try:
                next_idx = self.next_index.get(peer_id, 0)
                prev_log_index = next_idx - 1
                prev_log_term = self.log[prev_log_index][0] if prev_log_index >= 0 and self.log else 0
                
                # Get entries to send
                entries = self.log[next_idx:] if next_idx < len(self.log) else []
                
                # Convert entries to protobuf format
                pb_entries = []
                for term, command in entries:
                    log_entry = exp_pb2.LogEntry(
                        term=term,
                        command=json.dumps(command)
                    )
                    pb_entries.append(log_entry)
                
                request = exp_pb2.AppendEntriesRequest(
                    term=self.current_term,
                    leader_id=self.node_id,
                    prev_log_index=prev_log_index,
                    prev_log_term=prev_log_term,
                    entries=pb_entries,
                    leader_commit=self.commit_index
                )
                
                response = stub.AppendEntries(request, timeout=10)
                
                if response.success:
                    # Update nextIndex and matchIndex for this follower
                    if pb_entries:
                        self.next_index[peer_id] = next_idx + len(pb_entries)
                        self.match_index[peer_id] = self.next_index[peer_id] - 1
                else:
                    # If AppendEntries fails because of log inconsistency
                    if self.next_index[peer_id] > 0:
                        self.next_index[peer_id] -= 1
                
                # If we discover a higher term, revert to follower
                if response.term > self.current_term:
                    self.current_term = response.term
                    self.state = NodeState.FOLLOWER
                    self.voted_for = None
                    self.leader_id = None
                    self._persist_raft_state()
                    logger.info(f"Node {self.node_id} reverted to follower (higher term)")
                    return
                
            except Exception as e:
                logger.warning(f"Failed to send AppendEntries to {peer_id}: {str(e)}")
        
        # Update commit index based on matchIndex values
        self._update_commit_index()
        
        # Reset heartbeat timer
        self.last_heartbeat = time.time()
    
    def _update_commit_index(self):
        """Update the commit index based on matchIndex values."""
        if self.state != NodeState.LEADER:
            return
        
        # Sort matchIndex values in descending order
        match_indices = sorted([self.match_index[peer_id] for peer_id in self.peers], reverse=True)
        
        # Find the highest index that has been replicated to a majority of servers
        majority_idx = match_indices[len(self.peers) // 2]
        
        # Only update commit index for entries from current term
        for i in range(self.commit_index + 1, majority_idx + 1):
            if i < len(self.log) and self.log[i][0] == self.current_term:
                self.commit_index = i
                self._persist_raft_state()
                break
    
    def _apply_committed_entries(self):
        """Apply committed log entries to the state machine."""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            
            if self.last_applied < len(self.log):
                entry = self.log[self.last_applied]
                self._apply_command(entry[1])
                
                logger.debug(f"Applied command at index {self.last_applied}")
    
    def _apply_command(self, command: Dict):
        """Apply a command to the state machine."""
        cmd_type = command.get("type")
        
        if cmd_type == "CREATE_ACCOUNT":
            username = command["username"]
            password_hash = command["password_hash"]
            user_id = command["user_id"]
            
            # Create user
            user = User(user_id, username, password_hash)
            self.user_base.users[user_id] = user
            self.user_trie.add(username, user)
            
            # Persist user
            self._persist_user(user)
            
        elif cmd_type == "DELETE_ACCOUNT":
            user_id = command["user_id"]
            
            if user_id in self.user_base.users:
                user = self.user_base.users[user_id]
                
                # Delete from database
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM session_tokens WHERE user_id = ?", (user_id,))
                conn.commit()
                conn.close()
                
                # Delete from memory
                self.user_trie.delete(user.username)
                del self.user_base.users[user_id]
                if user_id in self.session_tokens.tokens:
                    del self.session_tokens.tokens[user_id]
                
                # Handle deletion of associated data (messages, etc.)
                # In a real implementation, you might want to cascade delete messages
                
        elif cmd_type == "SEND_MESSAGE":
            
            message_id = command["message_id"]
            sender_id = command["sender_id"]
            receiver_id = command["receiver_id"]
            content = command["content"]
            timestamp = command["timestamp"]

            logger.info(f"(raft_node.py): _apply_command => SEND_MESSAGE from {sender_id} to {receiver_id}")
            logger.info(f"(raft_node.py): Inserting message id={message_id} into message_base and conversations.")
           
            # Create message
            message = Message(
                message_id,
                content,
                sender_id,
                receiver_id,
                False,  # Not read yet
                timestamp
            )
            
            # Update state
            self.message_base.messages[message_id] = message

            # TODO: dump content of self.conversations before and after
            logger.info(f"(raft_node.py) Before append, keys={list(self.conversations.conversations.keys())}")
            # Update conversation
            conversation_key = tuple(sorted([sender_id, receiver_id]))
            self.conversations.conversations[conversation_key].append(message)
            
            logger.info(
                f"(raft_node.py) After append, keys={list(self.conversations.conversations.keys())}. "
                f"Added conversation_key={conversation_key} message_id={message_id}"
            )
            
            # Update unread messages for receiver
            if receiver_id in self.user_base.users:
                self.user_base.users[receiver_id].add_unread_message(message_id)
                
                # Update recent conversants
                if sender_id in self.user_base.users:
                    self.user_base.users[sender_id].update_recent_conversant(receiver_id)
                    self.user_base.users[receiver_id].update_recent_conversant(sender_id)
                    
                    # Persist updated users
                    self._persist_user(self.user_base.users[sender_id])
                    self._persist_user(self.user_base.users[receiver_id])
            
            # Persist message
            self._persist_message(message)
            
        elif cmd_type == "MARK_READ":
            user_id = command["user_id"]
            message_id = command["message_id"]
            
            if message_id in self.message_base.messages:
                message = self.message_base.messages[message_id]
                message.has_been_read = True
                
                # Update user's unread messages
                if user_id in self.user_base.users:
                    self.user_base.users[user_id].mark_message_read(message_id)
                    self._persist_user(self.user_base.users[user_id])
                
                # Persist updated message
                self._persist_message(message)
        
        elif cmd_type == "READ_MESSAGES":
            user_id = command["user_id"]
            count = command["count"]
            
            if user_id in self.user_base.users:
                user = self.user_base.users[user_id]
                marked_count = 0
                
                # Mark up to 'count' messages as read
                for _ in range(count):
                    if not user.unread_messages:
                        break
                    
                    message_id = user.unread_messages.popleft()
                    if message_id in self.message_base.messages:
                        self.message_base.messages[message_id].has_been_read = True
                        self._persist_message(self.message_base.messages[message_id])
                        marked_count += 1
                
                # Persist the updated user
                self._persist_user(user)
                
                logger.info(f"Marked {marked_count} messages as read for user {user_id}")
        
        elif cmd_type == "DELETE_MESSAGE":
            message_id = command["message_id"]
            
            if message_id in self.message_base.messages:
                message = self.message_base.messages[message_id]
                
                # Remove from conversations
                conversation_key = tuple(sorted([message.sender_id, message.receiver_id]))
                if conversation_key in self.conversations.conversations:
                    self.conversations.conversations[conversation_key] = [
                        msg for msg in self.conversations.conversations[conversation_key]
                        if msg.uid != message_id
                    ]
                
                # Remove from user's unread messages if applicable
                if message.receiver_id in self.user_base.users:
                    user = self.user_base.users[message.receiver_id]
                    if message_id in user.unread_messages:
                        user.mark_message_read(message_id)
                        self._persist_user(user)
                
                # Delete from database
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
                conn.commit()
                conn.close()
                
                # Remove from message base
                del self.message_base.messages[message_id]
                
                logger.info(f"Deleted message {message_id}")
    
    # RPC handlers
    
    def AppendEntries(self, request, context):
        """Handle AppendEntries RPC."""
        # Reset heartbeat timer since we heard from the leader
        self.last_heartbeat = time.time()
        
        # If term < currentTerm, reject
        if request.term < self.current_term:
            return exp_pb2.AppendEntriesResponse(term=self.current_term, success=False)
        
        # If we discover a higher term, update our term
        if request.term > self.current_term:
            self.current_term = request.term
            self.state = NodeState.FOLLOWER
            self.voted_for = None
            self._persist_raft_state()
        
        # Always accept current leader
        self.leader_id = request.leader_id
        
        # Log consistency check
        log_ok = (request.prev_log_index == -1 or 
                  (request.prev_log_index < len(self.log) and 
                   (request.prev_log_index == -1 or self.log[request.prev_log_index][0] == request.prev_log_term)))
        
        if not log_ok:
            return exp_pb2.AppendEntriesResponse(term=self.current_term, success=False)
        
        # Process entries
        if request.entries:
            # If existing entries conflict with new ones, delete them
            if request.prev_log_index + 1 < len(self.log):
                self.log = self.log[:request.prev_log_index + 1]
            
            # Append new entries
            for entry in request.entries:
                self.log.append((entry.term, json.loads(entry.command)))
                self._persist_log_entry(len(self.log) - 1, entry.term, json.loads(entry.command))
        
        # Update commit index
        if request.leader_commit > self.commit_index:
            self.commit_index = min(request.leader_commit, len(self.log) - 1)
            self._persist_raft_state()
        
        return exp_pb2.AppendEntriesResponse(term=self.current_term, success=True)
    
    def RequestVote(self, request, context):
        """Handle RequestVote RPC."""
        # If term < currentTerm, reject
        if request.term < self.current_term:
            return exp_pb2.RequestVoteResponse(term=self.current_term, vote_granted=False)
        
        # If term > currentTerm, update term and convert to follower
        if request.term > self.current_term:
            self.current_term = request.term
            self.state = NodeState.FOLLOWER
            self.voted_for = None
            self._persist_raft_state()
        
        # Determine if candidate's log is at least as up-to-date as ours
        last_log_index = len(self.log) - 1
        last_log_term = self.log[last_log_index][0] if self.log else 0
        
        log_ok = (request.last_log_term > last_log_term or 
                 (request.last_log_term == last_log_term and 
                  request.last_log_index >= last_log_index))
        
        # Grant vote if we haven't voted for someone else and log is ok
        vote_granted = (self.voted_for is None or self.voted_for == request.candidate_id) and log_ok
        
        if vote_granted:
            self.voted_for = request.candidate_id
            self.last_heartbeat = time.time()  # Reset timer when granting vote
            self._persist_raft_state()
        
        return exp_pb2.RequestVoteResponse(term=self.current_term, vote_granted=vote_granted)
    
    # Client-facing methods
    
    def create_account(self, username: str, password_hash: str) -> Tuple[bool, str]:
        logger.info("(raft_node.py): Attempting to create account for %s", username)
        """Create a new user account."""
        # Check if this node is the leader
        if self.state != NodeState.LEADER:
            if self.leader_id and self.leader_id in self.peers:
                logger.info("(raft_node.py): Node is not the leader. Attempting to forward request.")
                # Forward to leader
                try:
                    stub = self.peers[self.leader_id]
                    response = stub.CreateAccount(
                        exp_pb2.CreateAccountRequest(username=username, password_hash=password_hash))
                    return True, response.session_token
                except Exception as e:
                    logger.error(f"Failed to forward create_account to leader: {str(e)}")
                    return False, ""
            else:
                # No known leader, inform client
                return False, ""
        
        # Leader processing
        try:
            # Check if username exists
            logger.info(f"(raft_node.py): Checking if username {username} already exists: {self.user_trie.get(username)}")
            if self.user_trie.get(username):
                logger.info(f"(raft_node.py): Username {username} already exists")
                return False, "Username already exists"

            user_id = -1
            
            # Generate user ID
            if self.user_base._deleted_user_ids:
                user_id = self.user_base._deleted_user_ids.pop()
            else:
                user_id = self.user_base._next_user_id
                self.user_base._next_user_id += 1

            logger.info(f"(raft_node.py): Assigned user ID {user_id} for new account {username}")
                
            # Generate session token
            token = hashlib.sha256(f"{user_id}_{hash(time.time())}".encode()).hexdigest()
            self.session_tokens.tokens[user_id] = token
            
            # Persist session token
            self._persist_session_token(user_id, token)
            
            # Create log entry
            command = {
                "type": "CREATE_ACCOUNT",
                "username": username,
                "password_hash": password_hash,
                "user_id": user_id,
                "timestamp": int(time.time())
            }

            logger.info("(raft_node.py): Appending CREATE_ACCOUNT log entry for user %s", username)
            # Append to log
            self.log.append((self.current_term, command))
            self._persist_log_entry(len(self.log) - 1, self.current_term, command)

            logger.info("(raft_node.py): Successfully created account. Returning to client.")
            # Return success and session token
            return True, token
            
        except Exception as e:
            logger.error(f"Error in create_account: {str(e)}")
            return False, ""
    
    def login(self, username: str, password_hash: str) -> Tuple[bool, int, str, int]:
        """
        Log into an existing account.
        
        Args:
            username: Username to log in with
            password_hash: Hashed password to validate
            
        Returns:
            Tuple[bool, int, str, int]: (success, user_id, session_token, unread_count)
        """
        # This can work on any node, doesn't need to be the leader
        try:
            # Find the user
            user = self.user_trie.get(username)
            if not user:
                return (False, 0, "", 0)
                
            # Check password
            if user.passwordHash != password_hash:
                return (False, 0, "", 0)
                
            # Generate session token
            token = hashlib.sha256(f"{user.userID}_{hash(time.time())}".encode()).hexdigest()
            self.session_tokens.tokens[user.userID] = token
            
            # Persist session token
            self._persist_session_token(user.userID, token)
            
            # Return success info
            return (True, user.userID, token, len(user.unread_messages))
            
        except Exception as e:
            logger.error(f"Error in login: {str(e)}")
            return (False, 0, "", 0)
    
    def validate_session(self, user_id: int, session_token: str) -> bool:
        """
        Validate that a session token is valid for a user.
        
        Args:
            user_id: The user ID
            session_token: The session token to validate
            
        Returns:
            bool: True if the token is valid, False otherwise
        """
        # Check if the user exists
        if user_id not in self.user_base.users:
            return False
            
        # Check if the user has a session token
        if user_id not in self.session_tokens.tokens:
            return False
            
        # Check if the token matches
        return self.session_tokens.tokens[user_id] == session_token
    
    def list_accounts(self, wildcard: str) -> List[str]:
        """
        List accounts matching a wildcard pattern.
        
        Args:
            wildcard: Wildcard pattern to match usernames against
            
        Returns:
            List of matching usernames
        """
        # This can work on any node, doesn't need to be the leader
        try:
            matching_users = self.user_trie.regex_search(wildcard, return_values=False)
            return sorted(matching_users)
        except Exception as e:
            logger.error(f"Error in list_accounts: {str(e)}")
            return []
    
    def display_conversation(self, user_id: int, conversant_id: int) -> List[Message]:
        """
        Retrieve the conversation between two users.
        
        Args:
            user_id: First user ID
            conversant_id: Second user ID
            
        Returns:
            List of Message objects containing the conversation
        """
        # This can work on any node, doesn't need to be the leader
        logger.info(f"(raft_node.py): display_conversation called on node {self.node_id} between {user_id} and {conversant_id}")
        try:
            conversation_key = tuple(sorted([user_id, conversant_id]))
            if conversation_key in self.conversations.conversations:
                convo = self.conversations.conversations[conversation_key]
                logger.info(f"(raft_node.py): Found {len(convo)} messages in conversation {conversation_key}")
                return self.conversations.conversations[conversation_key]
            return []
        except Exception as e:
            logger.info(f"(raft_node.py): No conversation found for {conversation_key}")
            return []
    
    def send_message(self, sender_id: int, recipient_id: int, content: str) -> bool:
        """
        Send a message from one user to another.
        
        Args:
            sender_id: ID of the sender
            recipient_id: ID of the recipient
            content: Message content
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if this node is the leader
        if self.state != NodeState.LEADER:
            return False  # Only leader can process this
        
        try:
            # Check if sender and recipient exist
            if sender_id not in self.user_base.users or recipient_id not in self.user_base.users:
                return False
            
            # Generate message ID
            if self.message_base._deleted_message_ids:
                message_id = self.message_base._deleted_message_ids.pop()
            else:
                message_id = self.message_base._next_message_id
                self.message_base._next_message_id += 1
            
            # Create log entry
            command = {
                "type": "SEND_MESSAGE",
                "message_id": message_id,
                "sender_id": sender_id,
                "receiver_id": recipient_id,
                "content": content,
                "timestamp": int(time.time())
            }
            
            # Append to log
            appended_index = len(self.log)
            self.log.append((self.current_term, command))
            self._persist_log_entry(len(self.log) - 1, self.current_term, command)

            start_time = time.time()
            while True:
                # 1) 'commit_index' means the leader has determined it's safe to apply
                # 2) 'last_applied' means we *actually* ran _apply_command on it
                if self.commit_index >= appended_index and self.last_applied >= appended_index:
                    break

                # If we wait too long, we might want to time out
                if time.time() - start_time > 5.0:  # 5 second timeout, for example
                    logger.warning("Timed out waiting for SEND_MESSAGE entry to commit/apply.")
                    return False

                time.sleep(0.01)  # Sleep briefly to avoid busy loop

            return True
            
        except Exception as e:
            logger.error(f"Error in send_message: {str(e)}")
            return False
    
    def read_messages(self, user_id: int, count: int) -> bool:
        """
        Mark a number of messages as read.
        
        Args:
            user_id: User ID
            count: Number of messages to mark as read
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if this node is the leader
        if self.state != NodeState.LEADER:
            return False  # Only leader can process this
        
        try:
            # Check if user exists
            if user_id not in self.user_base.users:
                return False
            
            # Create log entry
            command = {
                "type": "READ_MESSAGES",
                "user_id": user_id,
                "count": count,
                "timestamp": int(time.time())
            }
            
            # Append to log
            self.log.append((self.current_term, command))
            self._persist_log_entry(len(self.log) - 1, self.current_term, command)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in read_messages: {str(e)}")
            return False
    
    def mark_message_as_read(self, user_id: int, message_id: int) -> bool:
        """
        Mark a specific message as read.
        
        Args:
            user_id: User ID
            message_id: Message ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if this node is the leader
        if self.state != NodeState.LEADER:
            return False  # Only leader can process this
        
        try:
            # Check if user and message exist
            if user_id not in self.user_base.users or message_id not in self.message_base.messages:
                return False
            
            # Create log entry
            command = {
                "type": "MARK_READ",
                "user_id": user_id,
                "message_id": message_id,
                "timestamp": int(time.time())
            }
            
            # Append to log
            self.log.append((self.current_term, command))
            self._persist_log_entry(len(self.log) - 1, self.current_term, command)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in mark_message_as_read: {str(e)}")
            return False
    
    def delete_message(self, message_id: int) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: Message ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if this node is the leader
        if self.state != NodeState.LEADER:
            return False  # Only leader can process this
        
        try:
            # Check if message exists
            if message_id not in self.message_base.messages:
                return False
            
            # Create log entry
            command = {
                "type": "DELETE_MESSAGE",
                "message_id": message_id,
                "timestamp": int(time.time())
            }
            
            # Append to log
            self.log.append((self.current_term, command))
            self._persist_log_entry(len(self.log) - 1, self.current_term, command)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in delete_message: {str(e)}")
            return False
    
    def delete_account(self, user_id: int) -> bool:
        """
        Delete a user account.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if this node is the leader
        if self.state != NodeState.LEADER:
            return False  # Only leader can process this
        
        try:
            # Check if user exists
            if user_id not in self.user_base.users:
                return False
            
            # Create log entry
            command = {
                "type": "DELETE_ACCOUNT",
                "user_id": user_id,
                "timestamp": int(time.time())
            }
            
            # Append to log
            self.log.append((self.current_term, command))
            self._persist_log_entry(len(self.log) - 1, self.current_term, command)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in delete_account: {str(e)}")
            return False
    
    def get_unread_messages(self, user_id: int) -> List[Tuple[int, int, int]]:
        """
        Get list of unread messages for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of tuples (message_id, sender_id, receiver_id)
        """
        # This can work on any node, doesn't need to be the leader
        try:
            if user_id not in self.user_base.users:
                return []
                
            user = self.user_base.users[user_id]
            result = []
            
            for msg_id in user.unread_messages:
                if msg_id in self.message_base.messages:
                    msg = self.message_base.messages[msg_id]
                    result.append((msg.uid, msg.sender_id, msg.receiver_id))
                    
            return result
            
        except Exception as e:
            logger.error(f"Error in get_unread_messages: {str(e)}")
            return []
    
    def get_message_info(self, user_id: int, message_id: int) -> Tuple[bool, int, str, int]:
        """
        Get information about a specific message.
        
        Args:
            user_id: User ID requesting the info
            message_id: Message ID
            
        Returns:
            Tuple[bool, int, str, int]: (read_flag, sender_id, content, timestamp)
        """
        # This can work on any node, doesn't need to be the leader
        try:
            # Check if message exists
            if message_id not in self.message_base.messages:
                return (False, 0, "", 0)
                
            # Get message
            msg = self.message_base.messages[message_id]
            
            # Check if user is sender or receiver
            if msg.sender_id != user_id and msg.receiver_id != user_id:
                return (False, 0, "", 0)  # User not authorized to view this message
                
            return (msg.has_been_read, msg.sender_id, msg.contents, msg.timestamp)
            
        except Exception as e:
            logger.error(f"Error in get_message_info: {str(e)}")
            return (False, 0, "", 0)
    
    def get_username_by_id(self, user_id: int) -> str:
        """
        Get username from user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            str: Username, or empty string if not found
        """
        # This can work on any node, doesn't need to be the leader
        try:
            if user_id in self.user_base.users:
                return self.user_base.users[user_id].username
            return ""
        except Exception as e:
            logger.error(f"Error in get_username_by_id: {str(e)}")
            return ""
    
    def get_user_by_username(self, username: str) -> Tuple[bool, Optional[int]]:
        """
        Get user ID from username.
        
        Args:
            username: Username to look up
            
        Returns:
            Tuple[bool, Optional[int]]: (found, user_id)
        """
        # This can work on any node, doesn't need to be the leader
        logger.info(f"(raft_node.py): get_user_by_username called on node {self.node_id} for {username}")
        try:
            user = self.user_trie.get(username)
            if user:
                logger.info(f"(raft_node.py): Found user ID {user.userID} for {username}")
                return (True, user.userID)
            return (False, None)
        except Exception as e:
            logger.info(f"(raft_node.py): No user found for {username}, error: {str(e)}")
            return (False, None)
    
    def stop(self):
        """Stop the node gracefully."""
        self.running = False
        if self.raft_thread.is_alive():
            self.raft_thread.join(timeout=10)
        
        logger.info(f"Stopping Raft node {self.node_id}")
