# Network Monitoring System

Ein vollständiges Netzwerk-Monitoring-System für lokale Netzwerke mit Web-Interface und Microsoft Teams Integration.

## Features

- 🔍 **Mehrere Check-Typen**
  - ICMP Ping für Erreichbarkeit
  - HTTP/HTTPS Endpoint-Überwachung
  - TCP Port-Checks (SSH, RDP, Datenbanken, etc.)

## Systemanforderungen

- Linux Server (Ubuntu, Debian, CentOS, etc.)
- Python 3.8 oder höher
- Systemd (für Service-Management)
- Netzwerkzugriff zu den zu überwachenden Geräten

## Installation

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/DEIN_USERNAME/studio-hilfe.git
cd studio-hilfe
```

### 2. Installation ausführen

```bash
chmod +x install.sh
./install.sh
```

Das Script führt folgende Schritte automatisch aus:
- Baut den Docker Container
- Startet den Service im Hintergrund
- Zeigt die lokale IP-Adresse an, unter der das Web-Interface erreichbar ist

### 3. Konfiguration anpassen

```bash
sudo nano /opt/network-monitor/config.yaml
```

### 4. Service starten

```bash
# Service starten
sudo systemctl start network-monitor

# Status prüfen
sudo systemctl status network-monitor

# Autostart aktivieren
sudo systemctl enable network-monitor
```

### 5. Web-Interface öffnen

Öffnen Sie einen Browser und navigieren Sie zu:

```
http://SERVER-IP:8000
```

Ersetzen Sie `SERVER-IP` mit der IP-Adresse Ihres Servers.

## Verwendung

### Logs anzeigen

```bash
# Live-Logs anzeigen
sudo journalctl -u network-monitor -f

# Letzte 100 Zeilen
sudo journalctl -u network-monitor -n 100

# Logs seit heute
sudo journalctl -u network-monitor --since today
```

### Service verwalten

```bash
# Service stoppen
sudo systemctl stop network-monitor

# Service neustarten
sudo systemctl restart network-monitor

# Service deaktivieren
sudo systemctl disable network-monitor
```

### Konfiguration neu laden

Nach Änderungen an der `config.yaml`:

```bash
sudo systemctl restart network-monitor
```

### Service startet nicht

```bash
# Detaillierte Logs anzeigen
sudo journalctl -u network-monitor -xe

# Konfiguration manuell testen
cd /opt/network-monitor
sudo -u monitor venv/bin/python api.py
```

### Port anpassen

Ändern Sie den Port in `config.yaml`:

```yaml
server:
  port: 8080  # Oder ein anderer freier Port
```

## Technische Details

### Architektur

- **Backend**: Python 3 mit FastAPI
- **Frontend**: Vanilla JavaScript mit WebSocket
- **Monitoring**: Asynchrone Checks mit asyncio
- **Benachrichtigungen**: Microsoft Teams Adaptive Cards
- **Deployment**: Systemd Service

### Abhängigkeiten

- FastAPI - Web Framework
- Uvicorn - ASGI Server
- httpx - HTTP Client
- aiohttp - Async HTTP
- PyYAML - Konfiguration
- websockets - WebSocket Support
### Erweiterungen

## Lizenz

Dieses Projekt steht zur freien Verfügung.
