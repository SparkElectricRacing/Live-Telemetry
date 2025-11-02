#!/bin/bash

echo "Stopping all services..."

pkill -f "uvicorn backend.server"
pkill -f "arduino_reader.py"
pkill -f "dashboard_app/main.py"
pkill -f "frontend/dashboard.py"

sleep 1

# Check if anything is still running
if ps aux | grep -E "(uvicorn backend.server|arduino_reader.py|dashboard_app/main.py|frontend/dashboard.py)" | grep -v grep > /dev/null; then
    echo "Some processes are still running, force killing..."
    pkill -9 -f "uvicorn backend.server"
    pkill -9 -f "arduino_reader.py"
    pkill -9 -f "dashboard_app/main.py"
    pkill -9 -f "frontend/dashboard.py"
fi

echo "All services stopped."
