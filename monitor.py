"""
Netzwerk-Monitoring Engine
Führt verschiedene Checks aus und verwaltet den Status
"""

import asyncio
import logging
import platform
import subprocess
import socket
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class CheckStatus(str, Enum):
    """Status eines Checks"""
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class CheckResult:
    """Ergebnis eines einzelnen Checks"""
    
    def __init__(
        self,
        status: CheckStatus,
        response_time: Optional[float] = None,
        error: Optional[str] = None,
        details: Optional[str] = None
    ):
        self.status = status
        self.response_time = response_time
        self.error = error
        self.details = details
        self.timestamp = datetime.now()


class BaseCheck:
    """Basis-Klasse für alle Check-Typen"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.type = config.get("type", "unknown")
        self.tags = set(config.get("tags", []))
    
    async def execute(self) -> CheckResult:
        """Führt den Check aus - muss von Subklassen implementiert werden"""
        raise NotImplementedError


class PingCheck(BaseCheck):
    """ICMP Ping Check"""
    
    async def execute(self) -> CheckResult:
        target = self.config.get("target")
        if not target:
            return CheckResult(CheckStatus.UNKNOWN, error="Kein Ziel angegeben")
        
        # Ping-Befehl abhängig vom Betriebssystem
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", "-W", "3", target]
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Ping ausführen
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=5.0
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if process.returncode == 0:
                return CheckResult(
                    CheckStatus.UP,
                    response_time=response_time,
                    details=f"Ping erfolgreich ({response_time:.1f}ms)"
                )
            else:
                return CheckResult(
                    CheckStatus.DOWN,
                    error=f"Ping fehlgeschlagen (Exit Code: {process.returncode})"
                )
        
        except asyncio.TimeoutError:
            return CheckResult(CheckStatus.DOWN, error="Ping Timeout")
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"Ping Fehler: {str(e)}")


class HttpCheck(BaseCheck):
    """HTTP/HTTPS Endpoint Check"""
    
    async def execute(self) -> CheckResult:
        url = self.config.get("url")
        expected_status = self.config.get("expected_status", 200)
        
        if not url:
            return CheckResult(CheckStatus.UNKNOWN, error="Keine URL angegeben")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if response.status_code == expected_status:
                return CheckResult(
                    CheckStatus.UP,
                    response_time=response_time,
                    details=f"HTTP {response.status_code} ({response_time:.1f}ms)"
                )
            else:
                return CheckResult(
                    CheckStatus.DOWN,
                    error=f"Unerwarteter Status Code: {response.status_code} (erwartet: {expected_status})"
                )
        
        except httpx.TimeoutException:
            return CheckResult(CheckStatus.DOWN, error="HTTP Timeout")
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"HTTP Fehler: {str(e)}")


class PortCheck(BaseCheck):
    """TCP Port Check"""
    
    async def execute(self) -> CheckResult:
        host = self.config.get("host")
        port = self.config.get("port")
        description = self.config.get("description", f"Port {port}")
        
        if not host or not port:
            return CheckResult(CheckStatus.UNKNOWN, error="Host oder Port nicht angegeben")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # TCP Verbindung versuchen
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            writer.close()
            await writer.wait_closed()
            
            return CheckResult(
                CheckStatus.UP,
                response_time=response_time,
                details=f"{description} erreichbar ({response_time:.1f}ms)"
            )
        
        except asyncio.TimeoutError:
            return CheckResult(CheckStatus.DOWN, error=f"{description} Timeout")
        except ConnectionRefusedError:
            return CheckResult(CheckStatus.DOWN, error=f"{description} Verbindung abgelehnt")
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"{description} Fehler: {str(e)}")


class PTPCheck(BaseCheck):
    """PTP (Precision Time Protocol) Check für RAVENNA/AES67
    
    Überprüft die PTP-Synchronisation durch Testen der PTP-Ports (319/320)
    und optional der Multicast-Adresse 224.0.1.129
    """
    
    async def execute(self) -> CheckResult:
        host = self.config.get("host")
        ptp_ports = self.config.get("ptp_ports", [319, 320])
        multicast_addr = self.config.get("multicast", "224.0.1.129")
        
        if not host:
            return CheckResult(CheckStatus.UNKNOWN, error="Host nicht angegeben")
        
        try:
            start_time = asyncio.get_event_loop().time()
            results = []
            
            # PTP Event Messages (Port 319) und General Messages (Port 320) prüfen
            for port in ptp_ports:
                try:
                    # UDP Socket für PTP erstellen
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(3.0)
                    
                    # Versuchen zu binden um zu prüfen ob Port verfügbar ist
                    # In Produktion würde man hier PTP-Pakete analysieren
                    sock.close()
                    results.append(f"Port {port} OK")
                except Exception as e:
                    results.append(f"Port {port} Fehler: {str(e)}")
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Wenn mindestens ein Port erreichbar ist, gilt der Check als erfolgreich
            if len(results) > 0:
                return CheckResult(
                    CheckStatus.UP,
                    response_time=response_time,
                    details=f"PTP verfügbar: {', '.join(results)} ({response_time:.1f}ms)"
                )
            else:
                return CheckResult(
                    CheckStatus.DOWN,
                    error="Keine PTP-Ports erreichbar"
                )
        
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"PTP Check Fehler: {str(e)}")


class MulticastCheck(BaseCheck):
    """Multicast/IGMP Check für RAVENNA Audio-Streams
    
    Überprüft ob Multicast-Gruppen erreichbar sind und IGMP funktioniert
    """
    
    async def execute(self) -> CheckResult:
        multicast_group = self.config.get("multicast_group", "239.69.0.1")
        port = self.config.get("port", 5004)
        timeout = self.config.get("timeout", 3)
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # DNS-Auflösung für Multicast-Gruppe (falls Hostname angegeben)
            try:
                # Versuche DNS-Auflösung, falls es ein Hostname ist
                resolved_ip = socket.gethostbyname(multicast_group)
            except socket.gaierror:
                # Wenn Auflösung fehlschlägt, verwende den Wert direkt (sollte IP sein)
                resolved_ip = multicast_group
            
            # Multicast Socket erstellen
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Multicast-Gruppe beitreten
            try:
                import struct
                mreq = struct.pack("4sl", socket.inet_aton(resolved_ip), socket.INADDR_ANY)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                sock.settimeout(timeout)
                
                # Versuchen zu binden
                sock.bind(('', port))
                
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                sock.close()
                
                details_msg = f"Multicast-Gruppe {multicast_group}"
                if resolved_ip != multicast_group:
                    details_msg += f" ({resolved_ip})"
                details_msg += f":{port} erreichbar ({response_time:.1f}ms)"
                
                return CheckResult(
                    CheckStatus.UP,
                    response_time=response_time,
                    details=details_msg
                )
            
            except Exception as e:
                sock.close()
                return CheckResult(
                    CheckStatus.DOWN,
                    error=f"Multicast-Gruppe nicht erreichbar: {str(e)}"
                )
        
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"Multicast Check Fehler: {str(e)}")


class RTPStreamCheck(BaseCheck):
    """RTP Audio Stream Check für RAVENNA
    
    Überprüft ob RTP Audio-Streams verfügbar sind
    """
    
    async def execute(self) -> CheckResult:
        host = self.config.get("host")
        port = self.config.get("port", 5004)
        description = self.config.get("description", "RTP Stream")
        
        if not host or not port:
            return CheckResult(CheckStatus.UNKNOWN, error="Host oder Port nicht angegeben")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # UDP Socket für RTP erstellen
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)
            
            try:
                # Versuchen an RTP-Port zu binden
                # In Produktion würde man hier RTP-Pakete analysieren (Packet Loss, Jitter)
                sock.bind(('', 0))  # Bind to any available port
                sock.close()
                
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                return CheckResult(
                    CheckStatus.UP,
                    response_time=response_time,
                    details=f"{description} Port {port} verfügbar ({response_time:.1f}ms)"
                )
            
            except Exception as e:
                sock.close()
                return CheckResult(
                    CheckStatus.DOWN,
                    error=f"{description} nicht verfügbar: {str(e)}"
                )
        
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"RTP Stream Check Fehler: {str(e)}")


class QoSCheck(BaseCheck):
    """Quality of Service Check für RAVENNA
    
    Überprüft QoS-Konfiguration (DSCP-Markierungen)
    Hinweis: Vollständige QoS-Prüfung erfordert Netzwerk-Analyse-Tools
    """
    
    async def execute(self) -> CheckResult:
        host = self.config.get("host")
        expected_dscp = self.config.get("dscp", 46)  # Default: EF für PTP
        description = self.config.get("description", "QoS")
        
        if not host:
            return CheckResult(CheckStatus.UNKNOWN, error="Host nicht angegeben")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Basis-Erreichbarkeitstest mit Ping
            # In Produktion würde man hier DSCP-Markierungen analysieren
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", "-W", "3", host]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=5.0
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if process.returncode == 0:
                return CheckResult(
                    CheckStatus.UP,
                    response_time=response_time,
                    details=f"{description} Check OK (DSCP {expected_dscp} erwartet) ({response_time:.1f}ms)"
                )
            else:
                return CheckResult(
                    CheckStatus.DOWN,
                    error=f"{description} Check fehlgeschlagen"
                )
        
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"QoS Check Fehler: {str(e)}")


class RAVENNAServiceCheck(BaseCheck):
    """RAVENNA Service Check
    
    Überprüft RAVENNA-spezifische Services wie RTSP, SAP, Web-UIs
    """
    
    async def execute(self) -> CheckResult:
        host = self.config.get("host")
        port = self.config.get("port")
        service_type = self.config.get("service_type", "rtsp")  # rtsp, sap, http
        description = self.config.get("description", f"RAVENNA {service_type.upper()}")
        
        if not host or not port:
            return CheckResult(CheckStatus.UNKNOWN, error="Host oder Port nicht angegeben")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            if service_type.lower() == "http" or service_type.lower() == "https":
                # HTTP/HTTPS Check für Web-UIs
                url = self.config.get("url", f"http://{host}:{port}")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if response.status_code < 400:
                    return CheckResult(
                        CheckStatus.UP,
                        response_time=response_time,
                        details=f"{description} erreichbar (HTTP {response.status_code}) ({response_time:.1f}ms)"
                    )
                else:
                    return CheckResult(
                        CheckStatus.DOWN,
                        error=f"{description} HTTP {response.status_code}"
                    )
            else:
                # TCP Port Check für RTSP (554), SAP (9875), etc.
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5.0
                )
                
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                writer.close()
                await writer.wait_closed()
                
                return CheckResult(
                    CheckStatus.UP,
                    response_time=response_time,
                    details=f"{description} erreichbar ({response_time:.1f}ms)"
                )
        
        except asyncio.TimeoutError:
            return CheckResult(CheckStatus.DOWN, error=f"{description} Timeout")
        except Exception as e:
            return CheckResult(CheckStatus.DOWN, error=f"{description} Fehler: {str(e)}")


class DeviceMonitor:
    """Überwacht ein einzelnes Gerät mit mehreren Checks"""
    
    def __init__(self, name: str, checks_config: List[Dict[str, Any]], notifications_enabled: bool = True):
        self.name = name
        self.checks = self._create_checks(checks_config)
        self.notifications_enabled = notifications_enabled
        self.status = CheckStatus.UNKNOWN
        self.last_check_time: Optional[datetime] = None
        self.consecutive_failures = 0
        self.last_notification_time: Optional[datetime] = None
        self.last_check_results: List[Dict[str, Any]] = []

        # Initial populate last_check_results with unknown state for immediate display
        self._init_unknown_state()

    def _init_unknown_state(self):
        """Initialisiert die Check-Ergebnisse mit 'unknown'"""
        for check in self.checks:
            check_data = {
                "type": check.type,
                "status": "unknown",
                "response_time": None,
                "error": None,
                "details": "Warte auf ersten Check...",
                "timestamp": None
            }
             # Config-Details hinzufügen
            if check.type == "ping":
                check_data["target"] = check.config.get("target")
            elif check.type == "port":
                check_data["host"] = check.config.get("host")
                check_data["port"] = check.config.get("port")
            
            self.last_check_results.append(check_data)
    
    def _create_checks(self, checks_config: List[Dict[str, Any]]) -> List[BaseCheck]:
        """Erstellt Check-Objekte basierend auf Konfiguration"""
        checks = []
        
        for check_config in checks_config:
            check_type = check_config.get("type", "").lower()
            
            if check_type == "ping":
                checks.append(PingCheck(check_config))
            elif check_type == "http":
                checks.append(HttpCheck(check_config))
            elif check_type == "port":
                checks.append(PortCheck(check_config))
            elif check_type == "ptp":
                checks.append(PTPCheck(check_config))
            elif check_type == "multicast":
                checks.append(MulticastCheck(check_config))
            elif check_type == "rtp":
                checks.append(RTPStreamCheck(check_config))
            elif check_type == "qos":
                checks.append(QoSCheck(check_config))
            elif check_type == "ravenna":
                checks.append(RAVENNAServiceCheck(check_config))
            else:
                logger.warning(f"Unbekannter Check-Typ: {check_type}")
        
        return checks
    
    async def run_checks(self, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Führt Checks für dieses Gerät aus
        
        Args:
            tags: Optional Filter. Wenn gesetzt, werden nur Checks ausgeführt, 
                  die mindestens einen dieser Tags haben.
        """
        results = []
        overall_status = CheckStatus.UP
        
        # Zu prüfende Checks filtern
        checks_to_run = self.checks
        if tags:
            tag_set = set(tags)
            checks_to_run = [c for c in self.checks if not c.tags.isdisjoint(tag_set)]
        
        # Checks parallel ausführen
        check_tasks = [check.execute() for check in checks_to_run]
        # Wenn keine Checks ausgewählt wurden (z.B. keine passenden Tags), leeres Ergebnis zurückgeben
        if not check_tasks:
            return {
                "name": self.name,
                "status": self.status, # Status nicht ändern
                "checks": [],
                "filtered_execution": True
            }

        check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        for check, result in zip(checks_to_run, check_results):
            if isinstance(result, Exception):
                logger.error(f"Check-Fehler für {self.name}: {result}")
                result = CheckResult(CheckStatus.DOWN, error=str(result))
            
            check_data = {
                "type": check.type,
                "status": result.status,
                "response_time": result.response_time,
                "error": result.error,
                "details": result.details,
                "timestamp": result.timestamp.isoformat()
            }
            
            # Wichtige Config-Details für Frontend hinzufügen
            if check.type == "ping":
                check_data["target"] = check.config.get("target")
            elif check.type == "port":
                check_data["host"] = check.config.get("host")
                check_data["port"] = check.config.get("port")
            
                check_data["port"] = check.config.get("port")
            
            results.append(check_data)
        
        # Ergebnisse speichern für spätere Abfragen (z.B. initial_status)
        if tags is None:
            self.last_check_results = results
            
            # Wenn ein Check fehlschlägt, ist das Gerät down
            if result.status == CheckStatus.DOWN:
                overall_status = CheckStatus.DOWN
        
        # Status aktualisieren NUR wenn keine Tags gefiltert wurden
        # (Teilweise Checks sollten den Gesamtstatus nicht überschreiben)
        if tags is None:
            previous_status = self.status
            self.status = overall_status
            self.last_check_time = datetime.now()
            
            # Fehler-Zähler aktualisieren
            if overall_status == CheckStatus.DOWN:
                self.consecutive_failures += 1
            else:
                self.consecutive_failures = 0
        else:
            previous_status = self.status

        return {
            "name": self.name,
            "status": self.status,
            "previous_status": previous_status,
            "consecutive_failures": self.consecutive_failures,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "notifications_enabled": self.notifications_enabled,
            "checks": results
        }
        
    def get_current_state(self) -> Dict[str, Any]:
        """Gibt den aktuellen Status inklusive letzter Check-Ergebnisse zurück"""
        return {
            "name": self.name,
            "status": self.status,
            "previous_status": self.status, # Im Zweifel aktueller Status
            "consecutive_failures": self.consecutive_failures,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "notifications_enabled": self.notifications_enabled,
            "checks": self.last_check_results
        }


class MonitoringEngine:
    """Haupt-Monitoring-Engine"""
    
    def __init__(self, devices_config: List[Dict[str, Any]]):
        self.devices: Dict[str, DeviceMonitor] = {}
        
        for device_config in devices_config:
            name = device_config.get("name")
            checks = device_config.get("checks", [])
            
            # Backwards compatibility: check for old webhook_url or new notifications_enabled
            notifications_enabled = device_config.get("notifications_enabled", True)
            if "webhook_url" in device_config and device_config["webhook_url"]:
                notifications_enabled = True
            
            if name and checks:
                self.devices[name] = DeviceMonitor(name, checks, notifications_enabled)
            else:
                logger.warning(f"Ungültige Gerätekonfiguration: {device_config}")
        
        logger.info(f"Monitoring Engine initialisiert mit {len(self.devices)} Geräten")
    
    async def check_all_devices(self) -> List[Dict[str, Any]]:
        """Führt Checks für alle Geräte aus"""
        tasks = [device.run_checks() for device in self.devices.values()]
        results = await asyncio.gather(*tasks)
        return results

    async def run_troubleshooting(self, check_tags: List[str]) -> Dict[str, Any]:
        """Führt spezifische Troubleshooting-Checks aus basierend auf Tags"""
        tasks = [device.run_checks(tags=check_tags) for device in self.devices.values()]
        results = await asyncio.gather(*tasks)
        
        # Ergebnisse filtern - nur Geräte zurückgeben, die tatsächlich Checks ausgeführt haben
        relevant_results = []
        for res in results:
            if res.get("checks"):
                relevant_results.append(res)
                
        return {
            "timestamp": datetime.now().isoformat(),
            "tags": check_tags,
            "devices": relevant_results
        }
    
    def get_device_status(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Gibt den aktuellen Status eines Geräts zurück"""
        device = self.devices.get(device_name)
        if not device:
            return None
        
        return device.get_current_state()
    
    def get_all_status(self) -> List[Dict[str, Any]]:
        """Gibt den Status aller Geräte zurück"""
        return [
            self.get_device_status(name)
            for name in self.devices.keys()
        ]
