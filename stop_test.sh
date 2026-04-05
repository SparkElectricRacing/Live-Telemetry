#!/bin/bash

echo "Stopping all services..."

pkill -f "serial_reader.py"
pkill -f "test_data_in.py"

sleep 1

# Check if anything is still running
if ps aux | grep -E "(uvicorn serial_reader.py|test_data_in.py)" | grep -v grep > /dev/null; then
    echo "Some processes are still running, force killing..."
    pkill -9 -f "serial_reader.py"
    pkill -9 -f "test_data_in.py"
fi

echo "All services stopped."
