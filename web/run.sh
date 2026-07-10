#!/bin/bash
# Run Quantum Werewolf web server

# Change to script directory
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r server/requirements.txt

# Run server
echo "Starting Quantum Werewolf server..."
echo "Open http://localhost:8000 in your browser"
echo ""
cd server
python main.py
