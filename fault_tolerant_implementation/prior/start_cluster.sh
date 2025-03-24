#!/bin/bash
# start_cluster.sh - Script to start a 5-node Raft cluster for 2-fault tolerance

# Create data directories if they don't exist
mkdir -p data/node1
mkdir -p data/node2
mkdir -p data/node3
mkdir -p data/node4
mkdir -p data/node5

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Starting 5-node Raft cluster for 2-fault tolerance..."

# Start node 1
echo "Starting node 1..."
python raft_server.py --node-id node1 --config cluster_config.json --data-dir data/node1 --port 50051 > logs/node1.log 2>&1 &
NODE1_PID=$!
echo "Node 1 started with PID $NODE1_PID"

# Wait a moment for the first node to initialize
sleep 10

# Start node 2
echo "Starting node 2..."
python raft_server.py --node-id node2 --config cluster_config.json --data-dir data/node2 --port 50052 > logs/node2.log 2>&1 &
NODE2_PID=$!
echo "Node 2 started with PID $NODE2_PID"

# Wait a moment
sleep 10

# Start node 3
echo "Starting node 3..."
python raft_server.py --node-id node3 --config cluster_config.json --data-dir data/node3 --port 50053 > logs/node3.log 2>&1 &
NODE3_PID=$!
echo "Node 3 started with PID $NODE3_PID"

# Wait a moment
sleep 10

# Start node 4
echo "Starting node 4..."
python raft_server.py --node-id node4 --config cluster_config.json --data-dir data/node4 --port 50054 > logs/node4.log 2>&1 &
NODE4_PID=$!
echo "Node 4 started with PID $NODE4_PID"

# Wait a moment
sleep 10

# Start node 5
echo "Starting node 5..."
python raft_server.py --node-id node5 --config cluster_config.json --data-dir data/node5 --port 50055 > logs/node5.log 2>&1 &
NODE5_PID=$!
echo "Node 5 started with PID $NODE5_PID"

# Write PIDs to a file for later cleanup
echo "$NODE1_PID $NODE2_PID $NODE3_PID $NODE4_PID $NODE5_PID" > cluster_pids.txt

echo "Cluster is now running. PIDs: $NODE1_PID $NODE2_PID $NODE3_PID $NODE4_PID $NODE5_PID"
echo "To stop the cluster, run: kill \$(cat cluster_pids.txt)"

echo "Waiting for cluster to stabilize and elect a leader..."
sleep 10
echo "Cluster should now be stable with an elected leader."

# Create a helper script to monitor logs
cat > monitor_logs.sh << 'EOL'
#!/bin/bash
# monitor_logs.sh - Monitors all node logs in real-time

if [ ! -d "logs" ]; then
  echo "Error: logs directory not found"
  exit 1
fi

if command -v multitail > /dev/null 2>&1; then
  # Use multitail if available
  multitail -s 2 logs/node*.log
else
  # Fallback to tail
  tail -f logs/node*.log
fi
EOL

chmod +x monitor_logs.sh
echo "Created monitor_logs.sh to watch all node logs"

# Create a helper script to kill specific nodes
cat > kill_node.sh << 'EOL'
#!/bin/bash
# kill_node.sh - Kill a specific node to test fault tolerance
# Usage: ./kill_node.sh <node_number>

if [ $# -ne 1 ]; then
  echo "Usage: $0 <node_number>"
  echo "Example: $0 1    # Kills node 1"
  exit 1
fi

NODE_NUM=$1
NODE_PID=$(ps aux | grep "raft_server.py --node-id node$NODE_NUM" | grep -v grep | awk '{print $2}')

if [ -z "$NODE_PID" ]; then
  echo "Node $NODE_NUM is not running"
  exit 1
fi

echo "Killing node $NODE_NUM (PID: $NODE_PID)..."
kill $NODE_PID
echo "Node $NODE_NUM killed"
EOL

chmod +x kill_node.sh
echo "Created kill_node.sh to test fault tolerance"

# Create a helper script to restart a node
cat > restart_node.sh << 'EOL'
#!/bin/bash
# restart_node.sh - Restart a specific node
# Usage: ./restart_node.sh <node_number>

if [ $# -ne 1 ]; then
  echo "Usage: $0 <node_number>"
  echo "Example: $0 1    # Restarts node 1"
  exit 1
fi

NODE_NUM=$1
PORT=$((50050 + $NODE_NUM))

# Check if node is already running
NODE_PID=$(ps aux | grep "raft_server.py --node-id node$NODE_NUM" | grep -v grep | awk '{print $2}')
if [ ! -z "$NODE_PID" ]; then
  echo "Node $NODE_NUM is already running (PID: $NODE_PID)"
  echo "Please kill it first with: ./kill_node.sh $NODE_NUM"
  exit 1
fi

echo "Starting node $NODE_NUM on port $PORT..."
python raft_server.py --node-id node$NODE_NUM --config cluster_config.json --data-dir data/node$NODE_NUM --port $PORT > logs/node$NODE_NUM.log 2>&1 &
NEW_PID=$!

echo "Node $NODE_NUM restarted with PID $NEW_PID"
EOL

chmod +x restart_node.sh
echo "Created restart_node.sh to restart downed nodes"

echo "Your 5-node Raft cluster is ready for testing fault tolerance!"
echo ""
echo "Helper scripts:"
echo "  - ./monitor_logs.sh     # Watch logs from all nodes"
echo "  - ./kill_node.sh <num>  # Kill a specific node (1-5)"
echo "  - ./restart_node.sh <num>  # Restart a specific node (1-5)"
