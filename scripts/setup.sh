#!/bin/bash
# Setup script for Raspberry Pi deployment

set -e  # Exit on error

echo "╔════════════════════════════════════════╗"
echo "║  Punching Bag Setup Script             ║"
echo "║  For Raspberry Pi 2/3/4/5              ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /etc/rpi-issue ]; then
    echo "⚠️  Warning: Not running on Raspberry Pi. Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 0
    fi
fi

echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    mpg123 \
    i2c-tools \
    nginx

echo ""
echo "🔧 Setting up Python virtual environment..."
cd /home/pi/punching-bag/backend
python3 -m venv venv
source venv/bin/activate

echo ""
echo "📥 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "🗄️  Initializing database..."
python3 -c "from database import Database; db = Database('../data/punching_bag.db'); print('Database initialized')"

echo ""
echo "⚙️  Configuring API keys..."
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env with your API keys:"
    echo "   nano backend/.env"
    echo ""
    echo "   Add your:"
    echo "   - ANTHROPIC_API_KEY=sk-ant-..."
    echo "   - ELEVENLABS_API_KEY=..."
    echo ""
fi

echo ""
echo "🌐 Setting up systemd services..."

# Backend service
sudo tee /etc/systemd/system/punchingbag.service > /dev/null <<EOF
[Unit]
Description=Punching Bag Backend Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/punching-bag/backend
Environment="PATH=/home/pi/punching-bag/backend/venv/bin"
ExecStart=/home/pi/punching-bag/backend/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd service created"

# Enable I2C for accelerometer
echo ""
echo "🔌 Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

echo ""
echo "📝 Configuring Nginx..."

# Nginx configuration for frontend
sudo tee /etc/nginx/sites-available/punchingbag > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    # Frontend
    root /home/pi/punching-bag/frontend;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API proxy
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # WebSocket support
    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/punchingbag /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo ""
echo "🎯 Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable punchingbag
sudo systemctl start punchingbag
sudo systemctl enable nginx

echo ""
echo "✅ Setup complete!"
echo ""
echo "╔════════════════════════════════════════╗"
echo "║  Next Steps:                           ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "1. Edit API keys:"
echo "   nano /home/pi/punching-bag/backend/.env"
echo ""
echo "2. Restart service:"
echo "   sudo systemctl restart punchingbag"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status punchingbag"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u punchingbag -f"
echo ""
echo "5. Access dashboard:"
echo "   http://$(hostname -I | awk '{print $1}')"
echo "   or http://raspberrypi.local"
echo ""
echo "6. Connect accelerometer (see README.md)"
echo ""
