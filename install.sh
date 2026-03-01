#!/bin/bash

# PortChecker - Installation Script
# Run with: chmod +x install.sh && ./install.sh

echo "🔧 Starting installation of PortChecker..."

# Check requirements
if ! command -v docker &> /dev/null; then
    echo "❌ Docker was not found. Please install Docker and Docker Compose first."
    exit 1
fi

# Make scripts and dirs
chmod +x update.sh
mkdir -p data

# Stop and remove existing container if it exists (to avoid name conflicts)
echo "🧹 Cleaning up old installations..."
docker stop portchecker 2>/dev/null || true
docker rm portchecker 2>/dev/null || true
# Also clean up old name if present
docker stop studio-hilfe 2>/dev/null || true
docker rm studio-hilfe 2>/dev/null || true

# Build and start container
echo "🚀 Building and starting container..."
docker compose up -d --build

# Show status
if [ $? -eq 0 ]; then
    echo "✅ Installation successful!"
    
    # Get local IP
    if [[ "$OSTYPE" == "darwin"* ]]; then
        LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
    else
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    fi
    
    echo ""
    echo "The interface is available at:"
    echo "👉 http://$LOCAL_IP:8000"
    echo ""
    echo "To update later, simply run ./update.sh."
else
    echo "❌ Installation failed."
    echo "Please ensure the Docker daemon is running and you have sufficient permissions."
    exit 1
fi
