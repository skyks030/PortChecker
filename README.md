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

**Wichtige Konfigurationsschritte:**

#### Microsoft Teams Webhook URL

1. Öffnen Sie Ihren Teams Channel
2. Klicken Sie auf `...` → `Connectors` → `Incoming Webhook`
3. Erstellen Sie einen neuen Webhook und kopieren Sie die URL
4. Tragen Sie die URL in der Konfiguration ein:

```yaml
teams_webhook_url: "https://your-organization.webhook.office.com/webhookb2/..."
```

#### Geräte konfigurieren

Fügen Sie Ihre zu überwachenden Geräte hinzu:

```yaml
devices:
  - name: "Web Server"
    checks:
      - type: "ping"
        target: "192.168.1.10"
      - type: "http"
        url: "http://192.168.1.10"
        expected_status: 200
      - type: "port"
        host: "192.168.1.10"
        port: 80
```

**Check-Typen:**

- **ping**: ICMP Ping
  ```yaml
  - type: "ping"
    target: "192.168.1.1"
  ```

- **http**: HTTP/HTTPS Endpoint
  ```yaml
  - type: "http"
    url: "https://example.com"
    expected_status: 200
  ```

- **port**: TCP Port
  ```yaml
  - type: "port"
    host: "192.168.1.20"
    port: 5432
    description: "PostgreSQL"
  ```

- **ptp**: PTP Synchronisation (RAVENNA/AES67)
  ```yaml
  - type: "ptp"
    host: "192.168.1.100"
    ptp_ports: [319, 320]
    multicast: "224.0.1.129"
  ```

- **multicast**: Multicast/IGMP Check
  ```yaml
  - type: "multicast"
    multicast_group: "239.69.0.1"
    port: 5004
  ```

- **rtp**: RTP Audio-Stream
  ```yaml
  - type: "rtp"
    host: "192.168.1.100"
    port: 5004
    description: "RTP Audio Stream"
  ```

- **qos**: Quality of Service
  ```yaml
  - type: "qos"
    host: "192.168.1.100"
    dscp: 46  # EF für PTP oder 34 für Audio
    description: "PTP QoS"
  ```

- **ravenna**: RAVENNA-Services (RTSP, SAP, Web-UIs)
  ```yaml
  - type: "ravenna"
    host: "192.168.1.100"
    port: 554
    service_type: "rtsp"
    description: "RTSP Session Management"
  ```

### DNS-Namen Unterstützung

Alle Check-Typen unterstützen DNS-Namen zusätzlich zu IP-Adressen:

```yaml
devices:
  - name: "QSYS Core"
    checks:
      - type: "ping"
        target: "qsys-core.studio.local"  # DNS-Name statt IP
      - type: "ptp"
        host: "qsys-core.studio.local"
      - type: "http"
        url: "http://webserver.local"
```

**Vorteile:**
- Lesbarere Konfiguration
- Flexibilität bei IP-Änderungen
- Zentrale Verwaltung über DNS

**Hinweis:** Multicast-Adressen (z.B. 239.69.0.1, 224.0.1.129) sollten weiterhin als IP-Adressen angegeben werden.

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

## Konfigurationsoptionen

### Monitoring-Einstellungen

```yaml
monitoring:
  # Intervall zwischen Checks in Sekunden
  check_interval: 30
  
  # Timeout für einzelne Checks in Sekunden
  check_timeout: 10
  
  # Anzahl fehlgeschlagener Checks bevor Benachrichtigung
  failure_threshold: 2
  
  # Minimale Zeit zwischen Benachrichtigungen (Sekunden)
  notification_cooldown: 300
```

### Server-Einstellungen

```yaml
server:
  # Bind-Adresse (0.0.0.0 = alle Interfaces)
  host: "0.0.0.0"
  
  # Port für Web-Interface
  port: 8000
```

### RAVENNA/AES67 Einstellungen

```yaml
monitoring:
  ravenna:
    ptp_domain: 0  # PTP Domain Number (Standard: 0)
    ptp_multicast: "224.0.1.129"  # PTP Multicast-Adresse
    ptp_ports: [319, 320]  # PTP Event (319) und General Messages (320)
    audio_dscp: 34  # DSCP AF41 für Audio-Traffic
    ptp_dscp: 46    # DSCP EF für PTP-Traffic
```

**RAVENNA-Geräte-Beispiel:**

```yaml
devices:
  - name: "QSYS Core"
    checks:
      - type: "ping"
        target: "192.168.1.100"
      - type: "ptp"
        host: "192.168.1.100"
        ptp_ports: [319, 320]
      - type: "qos"
        host: "192.168.1.100"
        dscp: 46
        description: "PTP QoS"
  
  - name: "HAPI II D/A-Wandler"
    checks:
      - type: "ping"
        target: "192.168.1.101"
      - type: "ptp"
        host: "192.168.1.101"
      - type: "ravenna"
        host: "192.168.1.101"
        port: 554
        service_type: "rtsp"
      - type: "rtp"
        host: "192.168.1.101"
        port: 5004
```

## Troubleshooting

### Service startet nicht

```bash
# Detaillierte Logs anzeigen
sudo journalctl -u network-monitor -xe

# Konfiguration manuell testen
cd /opt/network-monitor
sudo -u monitor venv/bin/python api.py
```

### Teams-Benachrichtigungen funktionieren nicht

1. Prüfen Sie die Webhook URL in `config.yaml`
2. Testen Sie die URL manuell:
   ```bash
   curl -X POST -H 'Content-Type: application/json' \
     -d '{"text":"Test"}' \
     YOUR_WEBHOOK_URL
   ```
3. Prüfen Sie die Logs auf Fehler

### Geräte werden als offline angezeigt

1. Prüfen Sie die Netzwerkverbindung vom Server
2. Testen Sie manuell:
   ```bash
   ping 192.168.1.10
   curl http://192.168.1.10
   nc -zv 192.168.1.10 80
   ```
3. Prüfen Sie Firewall-Regeln

### Port 8000 bereits belegt

Ändern Sie den Port in `config.yaml`:

```yaml
server:
  port: 8080  # Oder ein anderer freier Port
```

## Firewall-Konfiguration

Falls eine Firewall aktiv ist, öffnen Sie den Port:

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 8000/tcp

# firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## Sicherheitshinweise

- Das Web-Interface hat **keine Authentifizierung**
- Verwenden Sie einen Reverse-Proxy (nginx/Apache) mit SSL für Produktionsumgebungen
- Beschränken Sie den Zugriff über Firewall-Regeln
- Die Teams Webhook URL ist sensibel - schützen Sie die `config.yaml`

## Deinstallation

```bash
# Service stoppen und deaktivieren
sudo systemctl stop network-monitor
sudo systemctl disable network-monitor

# Service-Datei entfernen
sudo rm /etc/systemd/system/network-monitor.service
sudo systemctl daemon-reload

# Installationsverzeichnis entfernen
sudo rm -rf /opt/network-monitor

# Benutzer entfernen (optional)
sudo userdel monitor
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

## Support & Entwicklung

### Logs für Support

```bash
# System-Informationen
uname -a
python3 --version

# Service-Status
sudo systemctl status network-monitor

# Logs
sudo journalctl -u network-monitor -n 200 --no-pager
```

### Erweiterungen

Das System kann einfach erweitert werden:

1. **Neue Check-Typen**: Erstellen Sie eine neue Klasse in `monitor.py`
2. **Zusätzliche Benachrichtigungen**: Erweitern Sie `notifications.py`
3. **API-Endpoints**: Fügen Sie neue Routen in `api.py` hinzu

## Lizenz

Dieses Projekt steht zur freien Verfügung.
