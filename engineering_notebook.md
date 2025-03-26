# Engineering Notebook

### March 22, 2024 — Initial Research and Planning

**Thought Process:**
- After learning about Raft and Paxos in lecture, needed to choose between them for implementation
- We decided to use Raft since it's a bit more simple to implement compared to Paxos. it has clearer leader election process, simpler log replication mechanism, and better documentation and examples
- We identified the key requirements:
  * System must be persistent
  * Must handle 2 node failures
  * Must work across multiple processes/machines

**Focus:**
- Research Raft consensus algorithm implementation details
- Plan system architecture. Thinking of:
  * Server component for consensus
  * Client component for user interaction
  * Data persistence layer
- Design initial database schema for storing:
  * User accounts
  * Messages
  * Session tokens
  * Raft log entries

**Key Decisions:**
1. Use Raft over Paxos for consensus
2. Implement in two main parts:
   - Server: Handles consensus and data storage
   - GUI: Provides user interface
3. Use SQLite for persistence:
   ```sql
   -- Core tables needed:
   CREATE TABLE users (
       user_id INTEGER PRIMARY KEY,
       username TEXT UNIQUE,
       password_hash TEXT,
       data TEXT
   );
   
   CREATE TABLE messages (
       message_id INTEGER PRIMARY KEY,
       sender_id INTEGER,
       receiver_id INTEGER,
       content TEXT,
       has_been_read INTEGER,
       timestamp INTEGER
   );
   ```

---

### March 23, 2024 — Initial Implementation and Testing

**Thought Process:**
- Started with `fault_tolerant_implementation` directory
- Focused on core Raft functionalit for leader election, log replication, and state persistence.
- Tested different timeout configurations:
  * Election timeouts
  * Heartbeat intervals
  * Connection retry delays
- Initial inplementation is in `fault_tolerant_implementation` directory. 

**Focus:**
1. Implemented basic Raft node (`raft_node.py`):
   ```python
   class RaftNode:
       def __init__(self, node_id, cluster_config, data_dir):
           self.state = NodeState.FOLLOWER
           self.current_term = 0
           self.voted_for = None
           self.leader_id = None
           self.log = []  # (term, command) entries
           self.commit_index = -1
   ```

2. Added cluster management:
   - Node state tracking
   - Peer communication
   - Leader election process
   - Log replication

3. Implemented testing:
   - 3-node cluster stability
   - Leader failure recovery
   - Network partition handling

**Key Decisions:**
1. Chose to use gRPC for inter-node communication
2. Implemented SQLite-based persistence from the start
3. Added comprehensive logging for debugging

---

### March 24, 2024 — Docker Implementation

**Thought Process:**
- Previous implementation had issues with process management, network configuration, and state persistence. Inplementing `docker_ver`. 
- Docker could solve these by isolating each node, managing networking, and handling persistence

**Focus:**
1. Created Docker infrastructure:
   - Base container configuration
   - Network setup
   - Volume mounting for persistence

2. Refactored networking:
   - Container discovery
   - Port mapping
   - Inter-container communication

3. Modified core components:
   - Updated connection handling
   - Added container health checks
   - Improved error recovery

**Key Decisions:**
1. Use Docker Compose for orchestration
2. Mount SQLite databases as volumes
3. Implement retry mechanisms for container startup

---

### March 25, 2024 — Refinements and GUI Integration

**Thought Process:**
- Need to improve:
  * System stability
  * Error handling
  * User experience
- Focus on making the system production-ready

**Focus:**
1. More logging:
   ```python
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s [%(levelname)s] %(message)s',
       handlers=[
           logging.FileHandler("raft_server.log"),
           logging.StreamHandler()
       ]
   )
   ```

2. Fixed bugs with heartbeat startup, election timing, and connection. 

3. Improved client implementation:
   ```python
   def ensure_connected(self):
       """Enhanced connection management with retries"""
       retries = 5
       while retries > 0:
           try:
               if self._connect_to_leader():
                   return True
               if self._connect_to_random_node():
                   return True
           except Exception as e:
               logger.error(f"Connection attempt failed: {e}")
           retries -= 1
           time.sleep(1)
       return False
   ```

4. GUI Integration: connecting with fault-tolerant client, error handling, and improving user feedback

**Key Decisions:**
1. Implemented more aggressive retry logic
2. Added detailed logging throughout
3. Enhanced error messages for better debugging

---

### March 26, 2024 — Testing and Documentation

**Thought Process:**
- Need comprehensive testing to ensure:
  * System reliability
  * Fault tolerance
  * Data consistency
- Document implementation details and design decisions

**Focus:**
1. Implemented test suites:
   - Basic functionality tests
   - Advanced multi-user scenarios
   - Fault tolerance validation
   - Performance testing

2. Added documentation on:
   - System architecture
   - Implementation details
   - Testing procedures
   - Deployment instructions

**Key Decisions:**
1. Created separate test categories:
   - Unit tests for components
   - Integration tests for system
   - Stress tests for reliability
2. Added detailed logging for debugging
3. Enhanced error handling and recovery

## Future Work

If we had more time, we'd want to focus on more of the following:

1. **Performance Optimization**
   - Implement batch processing for messages
   - Optimize database queries
   - Add caching layer

2. **Enhanced Monitoring**
   - Add metrics collection
   - Create monitoring dashboard
   - Implement alerting

3. **Scalability**
   - Support dynamic node addition/removal
   - Implement sharding for messages
   - Add load balancing
