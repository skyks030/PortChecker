#!/bin/bash

# Stop the current container if running
echo "Stoppe vorherigen Container..."
docker compose down

# Rebuild and start the container
echo "Baue und starte neuen Container..."
docker compose up -d --build

# Prune unused images to save space (optional, but good for frequent builds)
echo "Bereinige alte Images..."
docker image prune -f


# Get local IP address (works on macOS and Linux)
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}' || echo "localhost")

echo "Update abgeschlossen! Das Interface sollte unter http://$LOCAL_IP:8000 erreichbar sein."
