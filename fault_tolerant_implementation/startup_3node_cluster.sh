#!/bin/bash
# start_3node_cluster.sh - Minimal script to start a 3-node cluster for basic debugging

# 1) Kill any existing Raft processes
echo "Stopping any existing nodes..."
kill $(cat cluster_pids.txt 2>/dev/null) 2>/dev/null
pkill -f "raft_server.py"

# 2) Clean up data directories (remove old DBs/logs to start fresh)
rm -rf data logs cluster_pids.txt
mkdir -p data/node1 data/node2 data/node3
mkdir -p logs

# 3) Start node1
echo "Starting node1 (leader candidate) ..."
python raft_server.py \
    --node-id node1 \
    --config cluster_config_3.json \
    --data-dir data/node1 \
    --port 50051 > logs/node1.log 2>&1 &
NODE1_PID=$!
echo "node1 PID = $NODE1_PID"

# Wait a bit longer for node1 to fully initialize
sleep 10

# 4) Start node2
echo "Starting node2 ..."
python raft_server.py \
    --node-id node2 \
    --config cluster_config_3.json \
    --data-dir data/node2 \
    --port 50052 > logs/node2.log 2>&1 &
NODE2_PID=$!
echo "node2 PID = $NODE2_PID"

# Wait a bit
sleep 10

# 5) Start node3
echo "Starting node3 ..."
python raft_server.py \
    --node-id node3 \
    --config cluster_config_3.json \
    --data-dir data/node3 \
    --port 50053 > logs/node3.log 2>&1 &
NODE3_PID=$!
echo "node3 PID = $NODE3_PID"
sleep 10

# 6) Write PIDs to file
echo "$NODE1_PID $NODE2_PID $NODE3_PID" > cluster_pids.txt

echo "All 3 nodes started!"
echo "To stop the cluster: kill \$(cat cluster_pids.txt)"

# 7) Give them a chance to elect a leader
echo "Waiting 20 seconds for the cluster to stabilize..."
sleep 20

echo "Done. Check 'logs/node*.log' for leadership info."

