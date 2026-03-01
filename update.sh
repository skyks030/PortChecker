#!/bin/bash

# PortChecker - Update Script

echo "🔍 Checking for updates..."

# Fetch latest changes without merging
git fetch origin

# Check if there are updates
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u})

if [ $LOCAL = $REMOTE ]; then
    echo "✅ Already up to date. No changes necessary."
    exit 0
fi

echo "🔄 Update available! Starting update process..."

# Update code
echo "📥 Downloading changes..."
# Stash any local changes (conflicts prevention)
git stash
git pull

git pull

# Rebuild container
echo "🏗️ Rebuilding container..."
docker compose down
docker compose up -d --build
docker image prune -f

# Get local IP
if [[ "$OSTYPE" == "darwin"* ]]; then
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
else
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
fi

echo "✅ Update completed successfully!"
echo "The interface is available at: http://$LOCAL_IP:8000"
