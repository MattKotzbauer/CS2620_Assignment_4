# Fault-Tolerant Chat Application

A distributed chat application that implements 2-fault tolerance using the Raft consensus algorithm. The system can handle up to 2 node failures while maintaining consistency and availability.

## Features

- 2-fault tolerance using 5-node Raft cluster
- Persistent message storage
- Automatic leader election
- Message replication across nodes
- Dockerized deployment
- gRPC communication

## Prerequisites

- Docker and Docker Compose
- Python 3.8 or higher
- gRPC tools

## Installation

1. Install Docker and Docker Compose
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Building

1. Build the Docker image:
   ```bash
   docker build -t raft_server .
   ```

## Running the Application

1. Start the 5-node cluster:
   ```bash
   docker-compose up -d
   ```

2. Run the demo script:
   ```bash
   python demo.py
   ```

The demo will:
1. Create test accounts (alice, bob, charlie)
2. Send messages between users
3. Kill the leader node to demonstrate fault tolerance
4. Kill a second node to demonstrate 2-fault tolerance
5. Verify message persistence

## Architecture

### Components

1. **Raft Node (`raft_node.py`)**
   - Implements the Raft consensus algorithm
   - Handles leader election
   - Manages log replication
   - Maintains persistent state

2. **Fault-Tolerant Client (`fault_tolerant_client.py`)**
   - Automatically finds the leader node
   - Handles server failures
   - Retries operations on failure
   - Maintains client-side state

3. **gRPC Server (`raft_server.py`)**
   - Exposes the chat API
   - Handles client requests
   - Integrates with Raft consensus

### Data Persistence

Each node maintains its state in a separate volume mounted at `/app/data/nodeX`. This includes:
- Raft log
- Current term
- Voted for record
- Message store

### Fault Tolerance

The system can handle up to 2 node failures because:
1. Uses 5 nodes (2f + 1 = 5, where f = 2)
2. Requires majority for leader election (3 nodes)
3. Replicates data across all nodes
4. Persists state to disk

## Testing Fault Tolerance

1. The demo script automatically tests fault tolerance by:
   - Killing the leader node
   - Verifying a new leader is elected
   - Killing a second node
   - Verifying the system remains operational

2. Manual testing:
   ```bash
   # Kill the leader node
   docker-compose stop nodeX  # where X is the leader node number
   
   # Kill a second node
   docker-compose stop nodeY  # where Y is another node number
   
   # Verify system still works
   python demo.py
   ```

## Troubleshooting

1. If nodes fail to start:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

2. If demo fails:
   - Check node logs: `docker-compose logs nodeX`
   - Ensure all nodes are running: `docker-compose ps`
   - Verify network connectivity: `docker network inspect raft-net`

## Engineering Decisions

1. **Why 5 nodes?**
   - Provides 2-fault tolerance (2f + 1 = 5)
   - Balances reliability with operational overhead

2. **Why Docker?**
   - Easy deployment and scaling
   - Isolated environments
   - Simulates distributed system on single machine
   - Facilitates testing across multiple machines

3. **Why gRPC?**
   - Efficient binary protocol
   - Strong typing with Protocol Buffers
   - Bidirectional streaming support
   - Built-in error handling

4. **Why separate persistence per node?**
   - Avoids single point of failure
   - True distributed system
   - Each node maintains independent state

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details
