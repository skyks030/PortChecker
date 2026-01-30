#!/bin/bash

# Studio Hilfe - Installation Script

echo "🔧 Starte Installation von Studio Hilfe..."

# Check requirements
if ! command -v docker &> /dev/null; then
    echo "❌ Docker wurde nicht gefunden. Bitte installiere Docker und Docker Compose zuerst."
    exit 1
fi

# Make scripts executable
chmod +x update.sh

# Build and start container
echo "🚀 Baue und starte Container..."
docker compose up -d --build

# Show status
if [ $? -eq 0 ]; then
    echo "✅ Installation erfolgreich!"
    
    # Get local IP
    LOCAL_IP=$(hostname -I | awk '{print $1}' || echo "localhost")
    
    echo ""
    echo "Das Interface ist erreichbar unter:"
    echo "👉 http://$LOCAL_IP:8000"
    echo ""
    echo "Zum Aktualisieren später einfach ./update.sh ausführen."
else
    echo "❌ Fehler bei der Installation."
    exit 1
fi
