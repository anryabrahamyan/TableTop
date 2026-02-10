#!/bin/bash

# Validation Script - Check that all components are properly set up

echo "================================"
echo "TableTop Project Validation"
echo "================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CHECKS_PASSED=0
CHECKS_FAILED=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}✗${NC} $1 missing"
        ((CHECKS_FAILED++))
    fi
}

check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}✗${NC} $1 missing"
        ((CHECKS_FAILED++))
    fi
}

echo "1. Checking Core Files..."
check_file "app.py"
check_file "models.py"
check_file "database.py"
check_file "requirements.txt"
check_file ".env"

echo ""
echo "2. Checking Templates..."
check_file "templates/base.html"
check_file "templates/login.html"
check_file "templates/profile.html"
check_file "templates/credits.html"
check_file "templates/create_session.html"
check_file "templates/view_session.html"
check_file "templates/error.html"

echo ""
echo "3. Checking Test Files..."
check_file "test_models.py"
check_file "test_integration.py"

echo ""
echo "4. Checking Directories..."
check_directory "myenv"
check_directory "static"
check_directory "static/css"
check_directory "templates"

echo ""
echo "5. Checking Python Packages..."
if command -v python &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python is available"
    ((CHECKS_PASSED++))
    
    # Check for required packages
    python -c "import flask" 2>/dev/null && echo -e "${GREEN}✓${NC} Flask installed" && ((CHECKS_PASSED++)) || (echo -e "${RED}✗${NC} Flask not installed" && ((CHECKS_FAILED++)))
    python -c "import flask_sqlalchemy" 2>/dev/null && echo -e "${GREEN}✓${NC} Flask-SQLAlchemy installed" && ((CHECKS_PASSED++)) || (echo -e "${RED}✗${NC} Flask-SQLAlchemy not installed" && ((CHECKS_FAILED++)))
    python -c "import pytest" 2>/dev/null && echo -e "${GREEN}✓${NC} Pytest installed" && ((CHECKS_PASSED++)) || (echo -e "${RED}✗${NC} Pytest not installed" && ((CHECKS_FAILED++)))
else
    echo -e "${RED}✗${NC} Python not available"
    ((CHECKS_FAILED++))
fi

echo ""
echo "6. Checking Database..."
if [ -f "tabletop.db" ]; then
    echo -e "${GREEN}✓${NC} Database file exists (tabletop.db)"
    ((CHECKS_PASSED++))
else
    echo -e "${YELLOW}⚠${NC}  Database not initialized (will be created on first run)"
fi

echo ""
echo "================================"
echo "Validation Summary"
echo "================================"
echo -e "Passed: ${GREEN}${CHECKS_PASSED}${NC}"
echo -e "Failed: ${RED}${CHECKS_FAILED}${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Project is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start the application: bash start.sh"
    echo "2. Run tests: bash run_tests.sh"
    echo "3. Access the app at: http://localhost:5000"
else
    echo -e "${RED}Some checks failed. Please fix the issues above.${NC}"
fi
