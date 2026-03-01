"""
FastAPI REST API und WebSocket Server
Stellt Status-Informationen bereit und koordiniert Monitoring
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
import os

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from datetime import datetime

from monitor import MonitoringEngine
from notifications import TeamsNotifier

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Globale Variablen
monitoring_engine: MonitoringEngine = None
teams_notifier: TeamsNotifier = None
config: Dict[str, Any] = {}
userdata: Dict[str, Any] = {}
active_websockets: List[WebSocket] = []


def load_config() -> Dict[str, Any]:
    """Lädt die Basis-Konfiguration aus config.yaml"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Konfiguration: {e}")
        return {}

def load_userdata() -> Dict[str, Any]:
    """Lädt die Benutzerdaten aus data/userdata.yaml oder migriert von config.yaml"""
    global config
    userdata_path = "data/userdata.yaml"
    
    # Sicherstellen, dass der Ordner existiert
    os.makedirs("data", exist_ok=True)
    
    data = {}
    if os.path.exists(userdata_path):
        try:
            with open(userdata_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                # Wenn wir userdata haben, brauchen wir nur sicherstellen, dass die keys existieren
                if "devices" not in data:
                    data["devices"] = []
                if "teams_webhook_url" not in data:
                    data["teams_webhook_url"] = ""
        except Exception as e:
            logger.error(f"Fehler beim Laden der Userdata: {e}")
    else:
        # Migration from old config
        logger.info("Migriere Benutzerdaten aus config.yaml nach data/userdata.yaml...")
        data["devices"] = config.pop("devices", [])
        data["teams_webhook_url"] = config.pop("teams_webhook_url", "")
        
        # Save new userdata and update config.yaml
        save_userdata(data)
        save_config(config)
        
    return data

def save_config(new_config: Dict[str, Any]):
    """Speichert die Basis-Konfiguration in config.yaml"""
    try:
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(new_config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Konfiguration: {e}")
        raise

def save_userdata(new_data: Dict[str, Any]):
    """Speichert die Benutzerdaten in data/userdata.yaml"""
    os.makedirs("data", exist_ok=True)
    try:
        with open("data/userdata.yaml", "w", encoding="utf-8") as f:
            yaml.dump(new_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Userdata: {e}")
        raise

async def monitoring_loop():
    """Haupt-Monitoring-Loop - läuft kontinuierlich im Hintergrund"""
    global monitoring_engine, teams_notifier, config
    
    check_interval = config.get("monitoring", {}).get("check_interval", 30)
    failure_threshold = config.get("monitoring", {}).get("failure_threshold", 2)
    
    logger.info(f"Monitoring Loop gestartet (Intervall: {check_interval}s)")
    
    while True:
        try:
            # Broadcast start event
            if active_websockets:
                checking_started_data = {"type": "checking_started"}
                disconnected_during_start_broadcast = []
                for ws in active_websockets:
                    try:
                        await ws.send_json(checking_started_data)
                    except Exception:
                        disconnected_during_start_broadcast.append(ws)
                
                for ws in disconnected_during_start_broadcast:
                    active_websockets.remove(ws)

            # Alle Geräte prüfen
            results = await monitoring_engine.check_all_devices()
            
            # Ergebnisse verarbeiten und Benachrichtigungen senden
            for result in results:
                device_name = result["name"]
                current_status = result["status"]
                previous_status = result["previous_status"]
                consecutive_failures = result["consecutive_failures"]
                
                device = monitoring_engine.devices[device_name]
                
                # Benachrichtigung bei Status-Änderung
                if current_status != previous_status:
                    logger.info(f"Status-Änderung erkannt für {device_name}: {previous_status} -> {current_status} (Failures: {consecutive_failures}/{failure_threshold})")
                    
                    # Gerät ist ausgefallen
                    if current_status == "down" and consecutive_failures >= failure_threshold:
                        # Keine Cooldown-Prüfung mehr - jede Statusänderung wird gemeldet!
                        # Das stellt sicher, dass auch kurz aufeinanderfolgende Ausfälle verschiedener Server gemeldet werden.
                        should_notify = True
                        
                        logger.info(f"Entscheidung für {device_name}: Sende DOWN Benachrichtigung? {should_notify}")
                        
                        if should_notify:
                            # Fehlerdetails sammeln
                            failed_checks = [
                                c for c in result["checks"] 
                                if c["status"] == "down"
                            ]
                            error_msg = "; ".join([
                                f"{c['type']}: {c['error']}" 
                                for c in failed_checks
                            ])
                            
                            global_webhook_url = userdata.get("teams_webhook_url", "")
                            
                            logger.info(f"Benachrichtigungs-Evaluation für {device_name}. Master Enabled: {device.notifications_enabled}, Global Toggle Set: {device.use_global_webhook}, Specific Webhook Set: {bool(device.webhook_url)}")
                            
                            if device.notifications_enabled:
                                # 1. Globale Benachrichtigung
                                if global_webhook_url and device.use_global_webhook:
                                    try:
                                        logger.info(f"Sende DOWN-Benachrichtigung an globalen Webhook für {device_name}")
                                        temp_notifier = TeamsNotifier(global_webhook_url)
                                        await temp_notifier.send_device_down(
                                            device_name=device_name,
                                            check_type=failed_checks[0]["type"] if failed_checks else "unknown",
                                            error=error_msg
                                        )
                                    except Exception as e:
                                        logger.error(f"Fehler beim Senden der globalen Benachrichtigung: {e}")
                                        
                                # 2. Server-spezifische Benachrichtigung
                                if device.webhook_url:
                                    try:
                                        logger.info(f"Sende DOWN-Benachrichtigung an spezifischen Webhook für {device_name}")
                                        spec_notifier = TeamsNotifier(device.webhook_url)
                                        await spec_notifier.send_device_down(
                                            device_name=device_name,
                                            check_type=failed_checks[0]["type"] if failed_checks else "unknown",
                                            error=error_msg
                                        )
                                    except Exception as e:
                                        logger.error(f"Fehler beim Senden der spezifischen Benachrichtigung: {e}")
                                        
                                # Timestamp aktualisieren, egal ob 1 oder beide gesendet wurden
                                if (global_webhook_url and device.use_global_webhook) or device.webhook_url:
                                    device.last_notification_time = device.last_check_time
                                else:
                                    logger.info(f"Keine aktiven Webhooks für {device_name} (Global URL fehlt oder Haken nicht gesetzt, und spezifischer Webhook fehlt)")
                            else:
                                logger.info(f"Benachrichtigungen für {device_name} sind deaktiviert (Master Toggle).")
                    
                    # Gerät ist wieder online
                    elif current_status == "up" and previous_status == "down":
                        logger.info(f"Entscheidung für {device_name}: Sende UP Benachrichtigung")
                        successful_checks = [
                            c for c in result["checks"]
                            if c["status"] == "up"
                        ]
                        
                        global_webhook_url = userdata.get("teams_webhook_url", "")
                        
                        if device.notifications_enabled:
                            # 1. Globale Benachrichtigung
                            if global_webhook_url and device.use_global_webhook:
                                try:
                                    logger.info(f"Sende UP-Benachrichtigung an globalen Webhook für {device_name}")
                                    temp_notifier = TeamsNotifier(global_webhook_url)
                                    await temp_notifier.send_device_up(
                                        device_name=device_name,
                                        check_type=successful_checks[0]["type"] if successful_checks else "unknown"
                                    )
                                except Exception as e:
                                    logger.error(f"Fehler beim Senden der globalen Benachrichtigung: {e}")
                                    
                            # 2. Server-spezifische Benachrichtigung
                            if device.webhook_url:
                                try:
                                    logger.info(f"Sende UP-Benachrichtigung an spezifischen Webhook für {device_name}")
                                    spec_notifier = TeamsNotifier(device.webhook_url)
                                    await spec_notifier.send_device_up(
                                        device_name=device_name,
                                        check_type=successful_checks[0]["type"] if successful_checks else "unknown"
                                    )
                                except Exception as e:
                                    logger.error(f"Fehler beim Senden der spezifischen Benachrichtigung: {e}")
                                    
                            if (global_webhook_url and device.use_global_webhook) or device.webhook_url:
                                device.last_notification_time = device.last_check_time
            
            # Status an alle verbundenen WebSocket-Clients senden
            if active_websockets:
                status_data = {
                    "type": "status_update",
                    "devices": results
                }
                
                # An alle Clients senden (disconnected clients werden entfernt)
                disconnected = []
                for ws in active_websockets:
                    try:
                        await ws.send_json(status_data)
                    except Exception:
                        disconnected.append(ws)
                
                for ws in disconnected:
                    active_websockets.remove(ws)
            
            logger.info(f"Check-Zyklus abgeschlossen - {len(results)} Geräte geprüft")
        
        except Exception as e:
            logger.error(f"Fehler im Monitoring Loop: {e}", exc_info=True)
        
        # Warten bis zum nächsten Check
        await asyncio.sleep(check_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle Management - startet/stoppt Background Tasks"""
    global monitoring_engine, teams_notifier, config, userdata
    
    # Startup
    logger.info("Server wird gestartet...")
    
    # Konfiguration laden
    config = load_config()
    userdata = load_userdata()
    
    # Monitoring Engine initialisieren
    devices_config = userdata.get("devices", [])
    monitoring_engine = MonitoringEngine(devices_config)
    
    # Teams Notifier initialisieren
    webhook_url = userdata.get("teams_webhook_url", "")
    teams_notifier = TeamsNotifier(webhook_url)
    
    # Monitoring Loop als Background Task starten
    monitoring_task = asyncio.create_task(monitoring_loop())
    
    logger.info("Server gestartet und bereit!")
    
    yield
    
    # Shutdown
    logger.info("Server wird heruntergefahren...")
    monitoring_task.cancel()
    try:
        await monitoring_task
    except asyncio.CancelledError:
        pass


# FastAPI App erstellen
app = FastAPI(
    title="Network Monitor",
    description="Netzwerk-Monitoring-System mit Teams-Integration",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Gibt den aktuellen Status aller Geräte zurück"""
    return {
        "devices": monitoring_engine.get_all_status(),
        "total_devices": len(monitoring_engine.devices),
        "timestamp": asyncio.get_event_loop().time()
    }


@app.get("/api/devices")
async def get_devices() -> List[str]:
    """Gibt eine Liste aller überwachten Geräte zurück"""
    return list(monitoring_engine.devices.keys())


@app.get("/api/device/{device_name}")
async def get_device_status(device_name: str) -> Dict[str, Any]:
    """Gibt den Status eines spezifischen Geräts zurück"""
    status = monitoring_engine.get_device_status(device_name)
    if status is None:
        return {"error": "Device not found"}
    return status


class AddDeviceRequest(BaseModel):
    name: str
    host: str
    ports: List[int]
    webhook_url: Optional[str] = None
    use_global_webhook: bool = True
    notifications_enabled: bool = True
    ping_enabled: bool = True


@app.post("/api/devices")
async def add_device(request: AddDeviceRequest) -> Dict[str, Any]:
    """Fügt ein neues Gerät zur Überwachung hinzu"""
    global monitoring_engine, userdata
    
    # Prüfen ob Gerät bereits existiert
    if request.name in monitoring_engine.devices:
        raise HTTPException(status_code=400, detail="Device already exists")
    
    # Neue Checks erstellen
    checks = []
    
    # Ping Check
    if request.ping_enabled:
        checks.append({
            "type": "ping",
            "target": request.host,
            "tags": ["connection", "ping"]
        })
    
    # Port Checks
    for port in request.ports:
        checks.append({
            "type": "port",
            "host": request.host,
            "port": port,
            "description": f"Port {port}",
            "tags": ["app"]
        })
        
    # Neues Gerät Setup
    new_device_config = {
        "name": request.name,
        "checks": checks,
        "notifications_enabled": request.notifications_enabled,
        "webhook_url": request.webhook_url,
        "use_global_webhook": request.use_global_webhook
    }
    
    # If the frontend sends webhook_url as a boolean flag (hacky but compatible with request model)
    # Ideally we should update request model, but let's interpret webhook_url presence as "enable notifications"
    # Actually, let's update AddDeviceRequest to have notifications_enabled
    
    # Zu Config hinzufügen
    if "devices" not in userdata:
        userdata["devices"] = []
        
    userdata["devices"].append(new_device_config)
    
    try:
        # Config speichern
        save_userdata(userdata)
        
        # Monitoring Engine aktualisieren
        device_monitor = monitoring_engine.devices.get(request.name)
        if not device_monitor:
            from monitor import DeviceMonitor
            new_monitor = DeviceMonitor(
                request.name, 
                checks, 
                new_device_config["notifications_enabled"],
                new_device_config["webhook_url"],
                new_device_config["use_global_webhook"]
            )
            monitoring_engine.devices[request.name] = new_monitor
            
        logger.info(f"Neues Gerät hinzugefügt: {request.name}")
        
        return {
            "status": "success",
            "message": f"Device {request.name} added",
            "device": new_device_config
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Geräts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateDeviceRequest(BaseModel):
    new_name: Optional[str] = None
    host: str
    ports: List[int]
    notifications_enabled: bool
    use_global_webhook: bool = True
    webhook_url: Optional[str] = None
    ping_enabled: bool = True


@app.put("/api/devices/{device_name}")
async def update_device(device_name: str, request: UpdateDeviceRequest) -> Dict[str, Any]:
    """Aktualisiert ein bestehendes Gerät"""
    global monitoring_engine, userdata
    
    if device_name not in monitoring_engine.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Check rename conflict
    target_name = request.new_name if request.new_name else device_name
    if target_name != device_name and target_name in monitoring_engine.devices:
        raise HTTPException(status_code=400, detail="A device with this name already exists")
    
    # Gerät in Config finden
    device_config = next((d for d in userdata.get("devices", []) if d["name"] == device_name), None)
    if not device_config:
         raise HTTPException(status_code=500, detail="Inconsistent state: device in runtime but not in userdata")

    # Checks neu erstellen
    checks = []
    if request.ping_enabled:
        checks.append({
            "type": "ping",
            "target": request.host,
            "tags": ["connection", "ping"]
        })
    
    for port in request.ports:
        checks.append({
            "type": "port",
            "host": request.host,
            "port": port,
            "description": f"Port {port}",
            "tags": ["app"]
        })
        
    # Config aktualisieren
    device_config["name"] = target_name
    device_config["checks"] = checks
    device_config["notifications_enabled"] = request.notifications_enabled
    device_config["webhook_url"] = request.webhook_url
    device_config["use_global_webhook"] = request.use_global_webhook
    
    try:
        save_userdata(userdata)
        
        # Runtime aktualisieren
        # Altes Gerät entfernen
        del monitoring_engine.devices[device_name]
        
        # Neues Gerät erstellen
        from monitor import DeviceMonitor
        new_monitor = DeviceMonitor(
            target_name, 
            checks, 
            request.notifications_enabled,
            request.webhook_url
        )
        monitoring_engine.devices[target_name] = new_monitor
        
        logger.info(f"Gerät aktualisiert: {device_name} -> {target_name}")
        
        return {"status": "success", "message": f"Device updated"}
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Geräts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/devices/{device_name}")
async def delete_device(device_name: str) -> Dict[str, Any]:
    """Löscht ein Gerät"""
    global monitoring_engine, userdata
    
    if device_name not in monitoring_engine.devices:
        raise HTTPException(status_code=404, detail="Device not found")
        
    # Aus Config entfernen
    userdata["devices"] = [d for d in userdata.get("devices", []) if d["name"] != device_name]
    
    try:
        save_userdata(userdata)
        
        # Aus Runtime entfernen
        del monitoring_engine.devices[device_name]
        
        logger.info(f"Gerät gelöscht: {device_name}")
        return {"status": "success", "message": f"Device {device_name} deleted"}
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Geräts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        

class SettingsRequest(BaseModel):
    teams_webhook_url: str


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    """Gibt die globalen Einstellungen zurück"""
    return {
        "teams_webhook_url": userdata.get("teams_webhook_url", "")
    }


@app.post("/api/settings")
async def save_settings(request: SettingsRequest) -> Dict[str, Any]:
    """Speichert die globalen Einstellungen"""
    global teams_notifier, userdata
    
    userdata["teams_webhook_url"] = request.teams_webhook_url
    
    try:
        save_userdata(userdata)
        
        # Runtime aktualisieren
        teams_notifier.webhook_url = request.teams_webhook_url
        teams_notifier.enabled = bool(request.teams_webhook_url)
        
        return {"status": "success", "message": "Settings saved"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings/test-webhook")
async def test_webhook(request: SettingsRequest) -> Dict[str, Any]:
    """Sendet eine Test-Nachricht an den Webhook"""
    global teams_notifier
    
    success = await teams_notifier.send_test_notification(request.teams_webhook_url)
    
    if success:
        return {"status": "success", "message": "Test message sent"}
    else:
        raise HTTPException(status_code=500, detail="Could not send test message. Check the URL.")


@app.get("/api/version")
async def get_version() -> Dict[str, str]:
    """Gibt die aktuelle Version zurück"""
    try:
        with open("version.txt", "r") as f:
            version = f.read().strip()
        return {"version": version}
    except FileNotFoundError:
        return {"version": "unknown"}
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Version: {e}")
        return {"version": "error"}


@app.post("/api/test")
async def trigger_manual_test() -> Dict[str, Any]:
    """Löst einen manuellen Test aller Geräte aus"""
    global monitoring_engine
    logger.info("Manueller Test wurde ausgelöst")
    
    # Broadcast start
    if active_websockets:
        await broadcast_status({"type": "checking_started"})
    
    # Alle Geräte prüfen
    results = await monitoring_engine.check_all_devices()
    
    # Ergebnisse broadcasten (wird normalerweise im loop gemacht, aber hier manuell triggern wir return)
    # Der monitoring_loop läuft weiter, aber wir wollen sofortiges Feedback.
    # Da monitor.py Ergebnisse zurückgibt, können wir diese senden.
    
    status_update = {
        "type": "status_update",
        "timestamp": datetime.now().isoformat(),
        "devices": monitoring_engine.get_all_status()
    }
    
    if active_websockets:
        await broadcast_status(status_update)
    
    return {
        "status": "success",
        "message": "Test abgeschlossen",
        "devices_tested": len(results)
    }

async def broadcast_status(data: Dict[str, Any]):
    """Hilfsfunktion zum Senden an alle WebSockets"""
    global active_websockets
    if not active_websockets:
        return
        
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)


@app.get("/api/troubleshoot/options")
async def get_troubleshoot_options() -> List[Dict[str, Any]]:
    """Gibt die verfügbaren Troubleshooting-Kategorien zurück"""
    return config.get("troubleshooting", [])


@app.post("/api/troubleshoot/{category_id}")
async def run_troubleshooting(category_id: str) -> Dict[str, Any]:
    """Führt Checks für eine spezifische Troubleshooting-Kategorie aus"""
    troubleshooting_config = config.get("troubleshooting", [])
    category = next((c for c in troubleshooting_config if c["id"] == category_id), None)
    
    if not category:
        return {"error": "Category not found"}
        
    check_tags = category.get("check_tags", [])
    logger.info(f"Starte Troubleshooting für {category_id} (Tags: {check_tags})")
    
    results = await monitoring_engine.run_troubleshooting(check_tags)
    
    return {
        "category": category,
        "results": results
    }


@app.get("/api/ravenna/status")
async def get_ravenna_status() -> Dict[str, Any]:
    """Gibt den RAVENNA-Gesamtstatus zurück"""
    ravenna_devices = []
    
    for device_name, device in monitoring_engine.devices.items():
        # Prüfen ob Gerät RAVENNA-Checks hat
        has_ptp = any(check.type == "ptp" for check in device.checks)
        has_multicast = any(check.type == "multicast" for check in device.checks)
        has_rtp = any(check.type == "rtp" for check in device.checks)
        
        if has_ptp or has_multicast or has_rtp:
            ravenna_devices.append({
                "name": device_name,
                "status": device.status,
                "has_ptp": has_ptp,
                "has_multicast": has_multicast,
                "has_rtp": has_rtp
            })
    
    # Gesamtstatus berechnen
    all_up = all(d["status"] == "up" for d in ravenna_devices)
    
    return {
        "overall_status": "up" if all_up else "down",
        "total_ravenna_devices": len(ravenna_devices),
        "devices": ravenna_devices,
        "config": config.get("monitoring", {}).get("ravenna", {})
    }


@app.get("/api/ravenna/ptp")
async def get_ptp_status() -> Dict[str, Any]:
    """Gibt PTP-Synchronisations-Details zurück"""
    ptp_devices = []
    
    for device_name, device in monitoring_engine.devices.items():
        ptp_checks = [check for check in device.checks if check.type == "ptp"]
        
        if ptp_checks:
            ptp_devices.append({
                "name": device_name,
                "status": device.status,
                "last_check": device.last_check_time.isoformat() if device.last_check_time else None
            })
    
    ravenna_config = config.get("monitoring", {}).get("ravenna", {})
    
    return {
        "ptp_domain": ravenna_config.get("ptp_domain", 0),
        "ptp_multicast": ravenna_config.get("ptp_multicast", "224.0.1.129"),
        "ptp_ports": ravenna_config.get("ptp_ports", [319, 320]),
        "devices": ptp_devices,
        "total_synced": sum(1 for d in ptp_devices if d["status"] == "up")
    }


@app.get("/api/ravenna/streams")
async def get_stream_status() -> Dict[str, Any]:
    """Gibt Audio-Stream-Übersicht zurück"""
    stream_devices = []
    
    for device_name, device in monitoring_engine.devices.items():
        rtp_checks = [check for check in device.checks if check.type == "rtp"]
        multicast_checks = [check for check in device.checks if check.type == "multicast"]
        
        if rtp_checks or multicast_checks:
            stream_devices.append({
                "name": device_name,
                "status": device.status,
                "has_rtp": len(rtp_checks) > 0,
                "has_multicast": len(multicast_checks) > 0
            })
    
    return {
        "total_stream_devices": len(stream_devices),
        "devices": stream_devices,
        "active_streams": sum(1 for d in stream_devices if d["status"] == "up")
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket für Echtzeit-Updates"""
    await websocket.accept()
    active_websockets.append(websocket)
    
    logger.info(f"WebSocket Client verbunden (Total: {len(active_websockets)})")
    
    try:
        # Initialen Status senden
        initial_status = {
            "type": "initial_status",
            "devices": monitoring_engine.get_all_status()
        }
        await websocket.send_json(initial_status)
        
        # Auf Nachrichten warten (keep-alive)
        while True:
            data = await websocket.receive_text()
            # Echo für keep-alive
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        logger.info("WebSocket Client getrennt")
    except Exception as e:
        logger.error(f"WebSocket Fehler: {e}")
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


# Static files für Frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_root():
    """Hauptseite - liefert das Web-Interface"""
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    
    # Server-Konfiguration aus config.yaml laden
    try:
        cfg = load_config()
        server_config = cfg.get("server", {})
        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8000)
        
        logger.info(f"Starte Server auf {host}:{port}")
        
        uvicorn.run(
            "api:app",
            host=host,
            port=port,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Fehler beim Starten des Servers: {e}")
        raise
