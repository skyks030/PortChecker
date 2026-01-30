# Network Monitoring System

Ein vollständiges Netzwerk-Monitoring-System für lokale Netzwerke mit Web-Interface und Microsoft Teams Integration.

## Features

- 🔍 **Mehrere Check-Typen**
  - ICMP Ping für Erreichbarkeit
  - HTTP/HTTPS Endpoint-Überwachung
  - TCP Port-Checks (SSH, RDP, Datenbanken, etc.)

## Systemanforderungen

- Linux Server (Ubuntu, Debian, CentOS, etc.)
- Docker & Docker Compose
- Netzwerkzugriff zu den zu überwachenden Geräten

## Installation

### Repository klonen

```bash
git clone https://github.com/skyks030/PortChecker.git
cd PortChecker
chmod +x install.sh
./install.sh
```

### Konfiguration anpassen

Die Konfiguration befindet sich in `config.yaml` und wird automatisch eingebunden.

```bash
nano config.yaml
```

Änderungen erfordern einen Neustart des Containers (siehe unten).

## Updates

Um das System zu aktualisieren (neuere Version von GitHub laden):

```bash
./update.sh
```

Dieses Script:
- Sichert deine `config.yaml`
- Lädt die neuste Version von GitHub
- Stellt deine Konfiguration wieder her
- Baut den Container neu

## Verwendung

### Logs anzeigen

```bash
docker compose logs -f
```

### Neustarten

```bash
docker compose restart
```

### Stoppen

```bash
docker compose down
```

## Technische Details

### Architektur

- **Container**: Docker (Python 3.11 Slim)
- **Backend**: Python 3 mit FastAPI
- **Frontend**: Vanilla JavaScript mit WebSocket
- **Monitoring**: Asynchrone Checks mit asyncio
- **Status Persistence**: Docker Volumes

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
