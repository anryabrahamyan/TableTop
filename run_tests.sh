#!/bin/bash

# Set environment variables for tests
export DATABASE_URL="sqlite:///:memory:"
export FLASK_ENV="testing"

# Run unit tests
echo "Running unit tests..."
python myenv/bin/python -m pytest test_models.py -v

echo ""
echo "Running integration tests..."
python myenv/bin/python -m pytest test_integration.py -v

echo ""
echo "Running all tests with coverage..."
python myenv/bin/python -m pytest test_models.py test_integration.py -v --tb=short
