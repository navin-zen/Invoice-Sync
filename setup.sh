#!/usr/bin/env bash

# Exit on error
set -e

echo "Starting Installation for Invoice Sync Local UI..."

# 1. System Dependencies (Standard for this project)
echo "Checking system dependencies..."
# Add checks for python, node, pnpm, uv if needed
# For now, we assume standard Ubuntu/WSL environment as per README

# 2. Setup Backend (Python)
echo "Setting up Backend..."
cd server
if command -v uv &> /dev/null
then
    echo "Found uv, syncing dependencies..."
    uv sync
else
    echo "uv not found, using python3 venv and pip..."
    python3 -m venv .venv
    ./activator pip install setuptools
    ./activator pip install -r requirements.txt
fi
cd ..

# 3. Setup Frontend (NodeJS)
echo "Setting up Frontend..."
cd frontend
if command -v pnpm &> /dev/null
then
    echo "Found pnpm, installing and building..."
    pnpm install
    pnpm build-js
    pnpm build-css
else
    echo "pnpm not found. Please install pnpm first."
    exit 1
fi
cd ..

# 4. Initialize Database
echo "Initializing Database..."
cd server
bash scripts/reset_db.sh
cd ..

echo "Installation Complete!"
echo "To start the application, run:"
echo "cd server && ./activator .envs/.development ./manage.py runserver"
