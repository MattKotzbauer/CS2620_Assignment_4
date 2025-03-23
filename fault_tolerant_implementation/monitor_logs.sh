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
