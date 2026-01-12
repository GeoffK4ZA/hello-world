#!/bin/bash
# ===========================================
# Digital Geoff - Oracle Cloud Always Free Setup
# ===========================================
#
# This script sets up Digital Geoff on Oracle Cloud's
# Always Free tier ARM instance.
#
# FREE FOREVER:
# - 4 ARM (Ampere A1) cores
# - 24 GB RAM
# - 200 GB storage
# - 10 TB outbound data transfer/month
#
# Prerequisites:
# 1. Oracle Cloud account (free)
# 2. ARM VM created (VM.Standard.A1.Flex)
# 3. SSH access to the instance
#
# Run this script ON the Oracle Cloud instance.

set -e

echo "======================================"
echo "Digital Geoff - Oracle Cloud Setup"
echo "======================================"
echo ""

# Update system
echo "[1/8] Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "[2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# Install Docker Compose
echo "[3/8] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Install Ollama (for local LLM)
echo "[4/8] Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Pull Ollama models
echo "[5/8] Pulling Ollama models..."
ollama pull mistral:latest &
ollama pull qwen2.5:3b &
wait
echo "Models pulled successfully"

# Create application directory
echo "[6/8] Setting up application..."
APP_DIR=/opt/digital-geoff
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Clone or update repository
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR && git pull
else
    git clone https://github.com/GeoffK4ZA/hello-world.git $APP_DIR
fi

cd $APP_DIR

# Create data directories
mkdir -p data/sqlite data/chroma data/knowledge data/logs

# Copy environment template if not exists
if [ ! -f .env ]; then
    cp .env.zero-cost.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your credentials:"
    echo "   nano $APP_DIR/.env"
    echo ""
fi

# Setup systemd service for auto-start
echo "[7/8] Setting up systemd service..."
sudo tee /etc/systemd/system/digital-geoff.service > /dev/null <<EOF
[Unit]
Description=Digital Geoff AI Agent
After=docker.service ollama.service
Requires=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/docker-compose -f docker-compose.zero-cost.yml up
ExecStop=/usr/local/bin/docker-compose -f docker-compose.zero-cost.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Setup Ollama service
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama LLM Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# Configure firewall
echo "[8/8] Configuring firewall..."
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT

# Save iptables rules
sudo apt install -y iptables-persistent
sudo netfilter-persistent save

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit your environment file:"
echo "   nano $APP_DIR/.env"
echo ""
echo "2. Add your credentials:"
echo "   - GROQ_API_KEY (free at groq.com)"
echo "   - TELEGRAM_BOT_TOKEN (free from @BotFather)"
echo "   - TELEGRAM_ALLOWED_USERS (your Telegram user ID)"
echo ""
echo "3. Start Digital Geoff:"
echo "   sudo systemctl start digital-geoff"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status digital-geoff"
echo "   docker-compose -f docker-compose.zero-cost.yml logs -f"
echo ""
echo "5. Open Oracle Cloud firewall:"
echo "   - Go to Oracle Cloud Console"
echo "   - Networking > Virtual Cloud Networks"
echo "   - Security Lists > Add Ingress Rules"
echo "   - Add port 8000 (API), 443 (HTTPS)"
echo ""
echo "Your Digital Geoff will be available at:"
echo "   http://$(curl -s ifconfig.me):8000"
echo ""
