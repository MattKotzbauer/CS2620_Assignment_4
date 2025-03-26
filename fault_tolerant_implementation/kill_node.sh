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
