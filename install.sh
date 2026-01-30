#!/bin/bash

# PortChecker - Installation Script
# Ausführen mit: chmod +x install.sh && ./install.sh

echo "🔧 Starte Installation von PortChecker..."

# Check requirements
if ! command -v docker &> /dev/null; then
    echo "❌ Docker wurde nicht gefunden. Bitte installiere Docker und Docker Compose zuerst."
    exit 1
fi

# Make scripts executable
chmod +x update.sh

# Stop and remove existing container if it exists (to avoid name conflicts)
echo "🧹 Bereinige alte Installationen..."
docker stop portchecker 2>/dev/null || true
docker rm portchecker 2>/dev/null || true
# Also clean up old name if present
docker stop studio-hilfe 2>/dev/null || true
docker rm studio-hilfe 2>/dev/null || true

# Build and start container
echo "🚀 Baue und starte Container..."
docker compose up -d --build

# Show status
if [ $? -eq 0 ]; then
    echo "✅ Installation erfolgreich!"
    
    # Get local IP
    if [[ "$OSTYPE" == "darwin"* ]]; then
        LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
    else
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    fi
    
    echo ""
    echo "Das Interface ist erreichbar unter:"
    echo "👉 http://$LOCAL_IP:8000"
    echo ""
    echo "Zum Aktualisieren später einfach ./update.sh ausführen."
else
    echo "❌ Fehler bei der Installation."
    echo "Bitte stelle sicher, dass der Docker-Daemon läuft und du Berechtigung hast."
    exit 1
fi
