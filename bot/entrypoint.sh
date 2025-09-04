#!/bin/bash
set -e

# Wait for API to be ready
echo "Waiting for API to be ready..."
while ! nc -z localhost 8000; do
  echo "API is unavailable - sleeping"
  sleep 1
done
echo "API is up - continuing"

# Wait for IB Gateway port to be open
echo "Waiting for IB Gateway port to open..."
while ! nc -z localhost 4002; do
  echo "IB Gateway is unavailable - sleeping"
  sleep 2
done
echo "IB Gateway port is open."

# Additional wait to ensure login is completed
echo "Waiting for IB Gateway login to complete..."
sleep 30

# Start the trading bot (run from bot directory to fix imports)
echo "Starting Trading Bot..."
cd bot
exec uv run bot.py
