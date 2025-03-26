function wait_for_node() {
  local node_id="$1"
  local logfile="$2"
  local phrase="Server started as node $node_id"

  echo "Waiting for $node_id to be ready..."
  # poll the logfile up to 30 seconds
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

echo "Starting node1..."
python raft_server.py --node-id node1 --config cluster_config_3.json \
  --data-dir data/node1 --port 50051 > logs/node1.log 2>&1 &
NODE1_PID=$!
wait_for_node "node1" "logs/node1.log"

echo "Starting node2..."
python raft_server.py --node-id node2 --config cluster_config_3.json \
  --data-dir data/node2 --port 50052 > logs/node2.log 2>&1 &
NODE2_PID=$!
wait_for_node "node2" "logs/node2.log"

echo "Starting node3..."
python raft_server.py --node-id node3 --config cluster_config_3.json \
  --data-dir data/node3 --port 50053 > logs/node3.log 2>&1 &
NODE3_PID=$!
wait_for_node "node3" "logs/node3.log"
