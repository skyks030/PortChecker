# DNS-Namen Unterstützung - Test-Beispiele

Das Network Monitoring System unterstützt jetzt vollständig DNS-Namen zusätzlich zu IP-Adressen.

## Beispiel-Konfiguration mit DNS-Namen

```yaml
devices:
  # Beispiel mit DNS-Namen
  - name: "Web Server"
    checks:
      - type: "ping"
        target: "webserver.local"
      - type: "http"
        url: "http://webserver.local"
      - type: "port"
        host: "webserver.local"
        port: 80
  
  # RAVENNA mit DNS-Namen
  - name: "QSYS Core"
    checks:
      - type: "ping"
        target: "qsys-core.studio.local"
      - type: "ptp"
        host: "qsys-core.studio.local"
        ptp_ports: [319, 320]
      - type: "ravenna"
        host: "qsys-core.studio.local"
        port: 554
        service_type: "rtsp"
  
  # Gemischt: DNS-Namen und IP-Adressen
  - name: "HAPI II"
    checks:
      - type: "ping"
        target: "hapi-ii.studio.local"  # DNS-Name
      - type: "multicast"
        multicast_group: "239.69.0.1"   # IP-Adresse (Multicast)
        port: 5004
```

## Unterstützte Check-Typen

Alle Check-Typen unterstützen DNS-Namen:

- ✅ **ping**: DNS-Namen werden automatisch vom `ping` Befehl aufgelöst
- ✅ **http**: httpx unterstützt DNS-Namen nativ
- ✅ **port**: asyncio.open_connection löst DNS-Namen automatisch auf
- ✅ **ptp**: Verwendet Standard-Socket-Funktionen mit DNS-Unterstützung
- ✅ **multicast**: DNS-Auflösung wurde hinzugefügt (socket.gethostbyname)
- ✅ **rtp**: Verwendet Standard-Socket-Funktionen
- ✅ **qos**: Verwendet ping mit DNS-Unterstützung
- ✅ **ravenna**: HTTP-Variante und TCP-Variante unterstützen DNS

## Vorteile von DNS-Namen

1. **Lesbarkeit**: `qsys-core.studio.local` ist leichter zu merken als `192.168.1.100`
2. **Flexibilität**: IP-Adressen können sich ändern, DNS-Namen bleiben gleich
3. **Wartbarkeit**: Zentrale Verwaltung über DNS-Server
4. **Dokumentation**: Selbsterklärende Konfiguration

## Hinweise

- DNS-Auflösung erfolgt bei jedem Check (kein Caching)
- Bei DNS-Fehlern wird der Check als DOWN markiert
- Multicast-Gruppen sollten weiterhin IP-Adressen verwenden (z.B. 239.69.0.1)
- Für PTP-Multicast (224.0.1.129) sollte die IP-Adresse verwendet werden
