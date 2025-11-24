#!/bin/bash
# System test script - verifies all components work

echo "╔════════════════════════════════════════╗"
echo "║  Punching Bag System Test              ║"
echo "╚════════════════════════════════════════╝"
echo ""

ERRORS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function test_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

function test_fail() {
    echo -e "${RED}✗${NC} $1"
    ERRORS=$((ERRORS + 1))
}

function test_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Checking Python environment..."
if [ -d "backend/venv" ]; then
    test_pass "Virtual environment exists"
else
    test_fail "Virtual environment not found (run setup.sh first)"
fi

echo ""
echo "2. Checking Python packages..."
source backend/venv/bin/activate 2>/dev/null
if python3 -c "import flask" 2>/dev/null; then
    test_pass "Flask installed"
else
    test_fail "Flask not installed"
fi

if python3 -c "import anthropic" 2>/dev/null; then
    test_pass "Anthropic SDK installed"
else
    test_fail "Anthropic SDK not installed"
fi

if python3 -c "import elevenlabs" 2>/dev/null; then
    test_pass "ElevenLabs SDK installed"
else
    test_fail "ElevenLabs SDK not installed"
fi

echo ""
echo "3. Checking configuration..."
if [ -f "backend/.env" ]; then
    test_pass ".env file exists"

    # Check for API keys
    if grep -q "ANTHROPIC_API_KEY=sk-ant-" backend/.env; then
        test_pass "Anthropic API key configured"
    else
        test_fail "Anthropic API key not set in .env"
    fi

    if grep -q "ELEVENLABS_API_KEY=" backend/.env; then
        test_pass "ElevenLabs API key configured"
    else
        test_fail "ElevenLabs API key not set in .env"
    fi
else
    test_fail ".env file not found (copy from .env.example)"
fi

echo ""
echo "4. Checking database..."
if [ -f "data/punching_bag.db" ]; then
    test_pass "Database exists"
else
    test_warn "Database doesn't exist yet (will be created on first run)"
fi

echo ""
echo "5. Checking directories..."
for dir in backend frontend data scripts; do
    if [ -d "$dir" ]; then
        test_pass "$dir/ directory exists"
    else
        test_fail "$dir/ directory missing"
    fi
done

echo ""
echo "6. Checking system dependencies..."

# mpg123
if command -v mpg123 &> /dev/null; then
    test_pass "mpg123 installed"
else
    test_warn "mpg123 not found (run: sudo apt-get install mpg123)"
fi

# i2c-tools (only on Pi)
if [ -f /etc/rpi-issue ]; then
    if command -v i2cdetect &> /dev/null; then
        test_pass "i2c-tools installed"
    else
        test_warn "i2c-tools not found (run: sudo apt-get install i2c-tools)"
    fi

    # I2C enabled?
    if [ -e /dev/i2c-1 ]; then
        test_pass "I2C interface enabled"
    else
        test_warn "I2C not enabled (run: sudo raspi-config → Interface → I2C)"
    fi
fi

# nginx (only on Pi)
if command -v nginx &> /dev/null; then
    test_pass "Nginx installed"

    if systemctl is-active --quiet nginx; then
        test_pass "Nginx running"
    else
        test_warn "Nginx not running (run: sudo systemctl start nginx)"
    fi
else
    test_warn "Nginx not installed (needed for Pi deployment)"
fi

echo ""
echo "7. Checking systemd service (Pi only)..."
if [ -f /etc/systemd/system/punchingbag.service ]; then
    test_pass "Systemd service configured"

    if systemctl is-active --quiet punchingbag; then
        test_pass "Service is running"
    else
        test_warn "Service not running (run: sudo systemctl start punchingbag)"
    fi
else
    test_warn "Systemd service not configured (Pi deployment only)"
fi

echo ""
echo "8. Testing backend imports..."
cd backend
if python3 -c "from database import Database; print('OK')" 2>/dev/null | grep -q OK; then
    test_pass "Database module imports"
else
    test_fail "Database module import failed"
fi

if python3 -c "from services.character_generator import CharacterGenerator; print('OK')" 2>/dev/null | grep -q OK; then
    test_pass "Character generator imports"
else
    test_fail "Character generator import failed"
fi

if python3 -c "from services.punch_handler import PunchHandler; print('OK')" 2>/dev/null | grep -q OK; then
    test_pass "Punch handler imports"
else
    test_fail "Punch handler import failed"
fi
cd ..

echo ""
echo "9. Testing frontend..."
if [ -f "frontend/index.html" ]; then
    test_pass "Frontend HTML exists"
else
    test_fail "Frontend HTML missing"
fi

if [ -f "frontend/css/style.css" ]; then
    test_pass "Frontend CSS exists"
else
    test_fail "Frontend CSS missing"
fi

if [ -f "frontend/js/app.js" ]; then
    test_pass "Frontend JS exists"
else
    test_fail "Frontend JS missing"
fi

echo ""
echo "10. Checking network..."
if curl -s http://localhost:5000/api/health &> /dev/null; then
    test_pass "Backend API responding"
else
    test_warn "Backend not responding (is it running?)"
fi

echo ""
echo "════════════════════════════════════════"
echo "Test Summary"
echo "════════════════════════════════════════"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    echo ""
    echo "System is ready to use."
    echo ""
    echo "Next steps:"
    echo "  1. Start backend: cd backend && python3 app.py"
    echo "  2. Open frontend: http://localhost:5000"
    echo "  3. Create your first character!"
    exit 0
else
    echo -e "${RED}✗ $ERRORS test(s) failed${NC}"
    echo ""
    echo "Please fix the issues above before proceeding."
    echo "See QUICKSTART.md for detailed setup instructions."
    exit 1
fi
