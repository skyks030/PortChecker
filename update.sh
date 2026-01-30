#!/bin/bash

# PortChecker - Update Script

echo "🔍 Suche nach Updates..."

# Fetch latest changes without merging
git fetch origin

# Check if there are updates
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u})

if [ $LOCAL = $REMOTE ]; then
    echo "✅ Bereits auf dem neuesten Stand. Keine Änderungen notwendig."
    exit 0
fi

echo "🔄 Update verfügbar! Starte Update-Prozess..."

# Backup config
echo "💾 Sichere Konfiguration..."
cp config.yaml config.yaml.bak

# Update code
echo "📥 Lade Änderungen herunter..."
# Stash any local changes (conflicts prevention)
git stash
git pull

# Merge/Restore config
# Note: We prefer the user's local config over the incoming default one.
echo "♻️ Stelle Konfiguration wieder her..."
if [ -f config.yaml.bak ]; then
    mv config.yaml.bak config.yaml
fi

# Rebuild container
echo "🏗️ Baue Container neu..."
docker compose down
docker compose up -d --build
docker image prune -f

# Get local IP
if [[ "$OSTYPE" == "darwin"* ]]; then
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
else
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
fi

echo "✅ Update erfolgreich abgeschlossen!"
echo "Das Interface ist erreichbar unter: http://$LOCAL_IP:8000"
