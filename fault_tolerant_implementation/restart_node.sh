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
