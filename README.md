# CS2620_Assignment_4 - Fault-Tolerant Chat Application

A distributed chat application implemented using the Raft consensus protocol for fault tolerance and persistence. The system can handle up to 2 node failures while maintaining consistency and availability.

We have implemented a raft consensus algorithm that has leader election, log replication, safety, and handles membership change. The persistence is handled by SQLite database with users, messages, session tokens, the raft log entries and state. The client inplements the automatic leader discover, retrying requests, connection pooling, and detecting dead nodes. 

pset content in `/fault_tolerant_implementation/`
pset2 content in `/gRPC_implementation/`

## How to run

### Prerequisites

- Docker and Docker Compose
- Python 3.7+
- Required Python packages (installed via Docker)

### Starting the System

1. **Build and start containers**
   ```bash
   # Stop any running containers
   docker-compose down

   # Remove persistent data and logs
   rm -rf data/
   rm -f client.log

   # Build the Docker image
   docker build -t raft_server:latest .

   # Run the demo
   python3 ./demo.py
   ```

## File Structure

```
docker_ver/
├── Dockerfile                 # Docker config for building containers
├── docker-compose.yml         # Multi-container Docker config
├── requirements.txt          # Python pkg dependencies
├── cluster_config.json       # Server cluster config
├── cluster_config_client.json # Client config
│
├── # Implementation
├── raft_node.py             # Raft consensus
├── raft_server.py           # gRPC server
├── core_entities.py         # Core data entities (User, Message)
├── core_structures.py       # Data structures (UserBase, MessageBase)
│
├── # Client Implementation
├── fault_tolerant_client.py # Fault-tolerant client library
├── fault_tolerant_gui.py    # GUI client config
├── demo.py                  # Demo script for testing
│
├── # Protocol Definition
├── exp.proto               # gRPC protocol definition
├── exp_pb2.py             # Generated protocol code
├── exp_pb2_grpc.py        # Generated gRPC service code
│
├── # Data and Logs
├── data/                   # Persistent data storage
│   ├── node1/             # Node 1's data
│   ├── node2/             # Node 2's data
│   └── node3/             # Node 3's data
└── client.log             # Client-side logging
```

## Overview

The client itself sends requests through gRPC and connects with `cluster_config_client.json` to find nodes. It will follow the following steps:
- Try to connect to the leader
- If leader is not available, try to connect to a random node. Then update leader cache and retries request with new leader.
- If node is not available, try to connect to another random node
- If all nodes are unavailable, retry the process

The leader then gets the client request through `raft_server.py`, where leader adds the request to the log and replicates the lpg entry to the follower nodes. If the majority confirm the replication, then it'll commit the entry, commit to the database, and tell the followers to commit. Once this is successful, it'll return a success message to the client.

After the commit, the data will be persisted in the SQLite database, thus future read requests can be read from any node and the client will be able to get a consistent response. If the node fails, then the data stays safe on other nodes and the client will automatically reconnect to a new leader.

This allows us to implement:

1. **Fault Tolerance**: survives up to 2 node failures, automatically elects a leader, replicates logs across nodes, and there isn't a single point of failure.

2. **Persistence**: All data persists on SQLite db, survives the node restarts so it maintains message history.

3. **Consistency**: All operations go through the leader and automatically handles stale reads. This ensures consistency. 

### Components

1. **Raft Node (`raft_node.py`)**
   - Implements the Raft consensus algorithm
   - Manages distributed state and log replication
   - Handles leader election and log consistency
   - Provides persistent storage using SQLite

2. **Server (`raft_server.py`)**
   - Implements the gRPC messaging service
   - Delegates operations to the Raft node
   - Handles client requests and responses

3. **Client (`fault_tolerant_client.py`)**
   - Provides fault-tolerant client implementation
   - Automatically handles leader changes and node failures
   - Implements retry logic and connection management

### Testing

Our testing is handled in our main testing script `/docker_ver/demo.py`. Here, we test

- Creating and verifying a 5 node cluster
- Testing account creation and message sending
- Testing node failure
- Verifies data persistence
- Testing leader election
- Validating 2 fault tolerance

For unit testing, we have the basic unit tests we previously implemented in the previous pset.

## Debugging

### Logs

- Server logs: `raft_server.log`
- Client logs: `client.log`
- SQLite database: `data/node_<id>.db`