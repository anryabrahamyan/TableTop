#!/bin/bash

# TableTop Project Startup Script

echo "================================"
echo "TableTop Project Startup"
echo "================================"
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Activating virtual environment..."
    source myenv/bin/activate
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file with default settings..."
    cat > .env << 'EOF'
DATABASE_URL=sqlite:///tabletop.db
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
EOF
    echo ".env created successfully"
fi

# Install/update dependencies
echo ""
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Initialize database if needed
if [ ! -f tabletop.db ]; then
    echo ""
    echo "Initializing database..."
    python database.py
fi

# Start Flask app
echo ""
echo "Starting Flask application..."
echo "Access the app at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
