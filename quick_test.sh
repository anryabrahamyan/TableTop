#!/bin/bash

# Quick test script to verify basic app functionality

echo "================================"
echo "TableTop Project - Quick Test"
echo "================================"
echo ""

cd /Users/anri/Desktop/SWE-Anri-Abrahamyan/Project_code/tabletop-project

# Activate virtual environment if not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Activating virtual environment..."
    source myenv/bin/activate
fi

# Check if database exists
if [ ! -f tabletop.db ]; then
    echo "Initializing database..."
    python3 database.py
fi

echo ""
echo "Testing imports..."
python3 << 'EOF'
import sys
try:
    from app import app, db
    from models import Game, UserProfile, SessionLobby, SessionStatus
    print("✓ All imports successful")
    
    # Test app context
    with app.app_context():
        print("✓ Flask app context initialized")
        print("✓ Database configured")
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
    sys.exit(1)
EOF

echo ""
echo "Starting Flask app (press Ctrl+C to stop after verification)..."
echo "Once started, visit: http://localhost:5000/login"
echo ""
sleep 2

# Start the app
python3 app.py
