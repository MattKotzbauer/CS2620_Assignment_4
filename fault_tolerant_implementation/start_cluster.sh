#!/bin/bash
# start_5node_cluster.sh - Script to start a 5-node Raft cluster with improved startup logic

###
# 1. Helper function to wait for a node's log to show it has started
###
function wait_for_node() {
  local node_id="$1"
  local logfile="$2"
  local phrase="Server started as node $node_id"

  echo "Waiting for $node_id to be ready..."

  # Poll the logfile up to 30 seconds
  for i in {1..30}; do
      if grep -q "$phrase" "$logfile"; then
          echo "$node_id is ready!"
          return 0
      fi
      sleep 1
  done

  echo "ERROR: $node_id not ready after 30 seconds."
  exit 1
}

###
# 2. Kill anything already using the ports 50051..50055
###
echo "Killing processes on ports 50051..50055 if any..."
for port in 50051 50052 50053 50054 50055; do
  kill -9 $(lsof -ti tcp:$port 2>/dev/null) 2>/dev/null
done

###
# 3. Create data/log dirs
###
mkdir -p data/node1 data/node2 data/node3 data/node4 data/node5
mkdir -p logs

###
# 4. Start nodes one at a time, waiting for each to be ready
###
echo "Starting 5-node Raft cluster for 2-fault tolerance..."

# Node 1
echo "Starting node1 (port 50051)..."
python raft_server.py --node-id node1 \
  --config cluster_config.json \
  --data-dir data/node1 \
  --port 50051 \
  > logs/node1.log 2>&1 &
NODE1_PID=$!
wait_for_node "node1" "logs/node1.log"

# Node 2
echo "Starting node2 (port 50052)..."
python raft_server.py --node-id node2 \
  --config cluster_config.json \
  --data-dir data/node2 \
  --port 50052 \
  > logs/node2.log 2>&1 &
NODE2_PID=$!
wait_for_node "node2" "logs/node2.log"

# Node 3
echo "Starting node3 (port 50053)..."
python raft_server.py --node-id node3 \
  --config cluster_config.json \
  --data-dir data/node3 \
  --port 50053 \
  > logs/node3.log 2>&1 &
NODE3_PID=$!
wait_for_node "node3" "logs/node3.log"

# Node 4
echo "Starting node4 (port 50054)..."
python raft_server.py --node-id node4 \
  --config cluster_config.json \
  --data-dir data/node4 \
  --port 50054 \
  > logs/node4.log 2>&1 &
NODE4_PID=$!
wait_for_node "node4" "logs/node4.log"

# Node 5
echo "Starting node5 (port 50055)..."
python raft_server.py --node-id node5 \
  --config cluster_config.json \
  --data-dir data/node5 \
  --port 50055 \
  > logs/node5.log 2>&1 &
NODE5_PID=$!
wait_for_node "node5" "logs/node5.log"

# Store PIDs
echo "$NODE1_PID $NODE2_PID $NODE3_PID $NODE4_PID $NODE5_PID" > cluster_pids.txt

echo "All 5 nodes started. PIDs: $NODE1_PID $NODE2_PID $NODE3_PID $NODE4_PID $NODE5_PID"
echo "To stop the cluster, run: kill \$(cat cluster_pids.txt)"

echo "Creating helper scripts..."

###
# 5. Helper script to monitor logs
###
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
echo "  -> Created monitor_logs.sh (for watching all node logs)."

###
# 6. Helper script to kill a node
###
cat > kill_node.sh << 'EOL'
#!/bin/bash
# kill_node.sh - Kill a specific node to test fault tolerance
# Usage: ./kill_node.sh <node_number>

if [ $# -ne 1 ]; then
  echo "Usage: $0 <node_number>"
  echo "Example: $0 1    # Kills node1"
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
echo "  -> Created kill_node.sh (to kill a specific node)."

###
# 7. Helper script to restart a node
###
cat > restart_node.sh << 'EOL'
#!/bin/bash
# restart_node.sh - Restart a specific node
# Usage: ./restart_node.sh <node_number>

if [ $# -ne 1 ]; then
  echo "Usage: $0 <node_number>"
  echo "Example: $0 1    # Restarts node1"
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
python raft_server.py --node-id node$NODE_NUM \
  --config cluster_config.json \
  --data-dir data/node$NODE_NUM \
  --port $PORT \
  > logs/node$NODE_NUM.log 2>&1 &
NEW_PID=$!

echo "Node $NODE_NUM restarted with PID $NEW_PID"
EOL
chmod +x restart_node.sh
echo "  -> Created restart_node.sh (to restart downed nodes)."

echo ""
echo "Cluster startup complete!"
echo "Use ./monitor_logs.sh to view logs, or ./kill_node.sh / ./restart_node.sh to test failures."

