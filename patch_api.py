import re

with open("api.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update load_userdata
old_load = """    data = {}
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
        save_config(config)"""

new_load = """    data = {}
    if os.path.exists(userdata_path):
        try:
            with open(userdata_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                # Wenn wir userdata haben, brauchen wir nur sicherstellen, dass die keys existieren
                if "devices" not in data:
                    data["devices"] = []
                if "global_webhooks" not in data:
                    old_url = data.pop("teams_webhook_url", "")
                    if old_url:
                        data["global_webhooks"] = [{"alias": "Default", "url": old_url}]
                    else:
                        data["global_webhooks"] = []
                    
                    for device in data.get("devices", []):
                        if device.get("use_global_webhook", True):
                            device["global_webhooks"] = ["Default"]
                        elif "global_webhooks" not in device:
                            device["global_webhooks"] = []
                        if "use_global_webhook" in device:
                            del device["use_global_webhook"]
                    save_userdata(data)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Userdata: {e}")
    else:
        # Migration from old config
        logger.info("Migriere Benutzerdaten aus config.yaml nach data/userdata.yaml...")
        data["devices"] = config.pop("devices", [])
        old_url = config.pop("teams_webhook_url", "")
        
        if old_url:
            data["global_webhooks"] = [{"alias": "Default", "url": old_url}]
        else:
            data["global_webhooks"] = []
            
        for device in data.get("devices", []):
            if device.get("use_global_webhook", True):
                device["global_webhooks"] = ["Default"]
            elif "global_webhooks" not in device:
                device["global_webhooks"] = []
            if "use_global_webhook" in device:
                del device["use_global_webhook"]
        
        # Save new userdata and update config.yaml
        save_userdata(data)
        save_config(config)"""

content = content.replace(old_load, new_load)


# 2. Update DOWN notifications in monitoring_loop
old_down_notif = """                            global_webhook_url = userdata.get("teams_webhook_url", "")
                            
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
                                    logger.info(f"Keine aktiven Webhooks für {device_name} (Global URL fehlt oder Haken nicht gesetzt, und spezifischer Webhook fehlt)")"""

new_down_notif = """                            global_webhooks_list = userdata.get("global_webhooks", [])
                            global_webhooks_dict = {w["alias"]: w["url"] for w in global_webhooks_list}
                            
                            logger.info(f"Benachrichtigungs-Evaluation für {device_name}. Master Enabled: {device.notifications_enabled}, Global Webhooks Set: {device.global_webhooks}, Specific Webhook Set: {bool(device.webhook_url)}")
                            
                            if device.notifications_enabled:
                                sent_any = False
                                # 1. Globale Benachrichtigungen
                                for alias in device.global_webhooks:
                                    url = global_webhooks_dict.get(alias)
                                    if url:
                                        try:
                                            logger.info(f"Sende DOWN-Benachrichtigung an globalen Webhook '{alias}' für {device_name}")
                                            temp_notifier = TeamsNotifier(url)
                                            await temp_notifier.send_device_down(
                                                device_name=device_name,
                                                check_type=failed_checks[0]["type"] if failed_checks else "unknown",
                                                error=error_msg
                                            )
                                            sent_any = True
                                        except Exception as e:
                                            logger.error(f"Fehler beim Senden der globalen Benachrichtigung '{alias}': {e}")
                                        
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
                                        sent_any = True
                                    except Exception as e:
                                        logger.error(f"Fehler beim Senden der spezifischen Benachrichtigung: {e}")
                                        
                                # Timestamp aktualisieren, egal ob 1 oder beide gesendet wurden
                                if sent_any:
                                    device.last_notification_time = device.last_check_time
                                else:
                                    logger.info(f"Keine aktiven Webhooks für {device_name} (Global URLs fehlen, und spezifischer Webhook fehlt)")"""

content = content.replace(old_down_notif, new_down_notif)


# 3. Update UP notifications in monitoring_loop
old_up_notif = """                        global_webhook_url = userdata.get("teams_webhook_url", "")
                        
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
                                device.last_notification_time = device.last_check_time"""

new_up_notif = """                        global_webhooks_list = userdata.get("global_webhooks", [])
                        global_webhooks_dict = {w["alias"]: w["url"] for w in global_webhooks_list}
                        
                        if device.notifications_enabled:
                            sent_any = False
                            # 1. Globale Benachrichtigungen
                            for alias in device.global_webhooks:
                                url = global_webhooks_dict.get(alias)
                                if url:
                                    try:
                                        logger.info(f"Sende UP-Benachrichtigung an globalen Webhook '{alias}' für {device_name}")
                                        temp_notifier = TeamsNotifier(url)
                                        await temp_notifier.send_device_up(
                                            device_name=device_name,
                                            check_type=successful_checks[0]["type"] if successful_checks else "unknown"
                                        )
                                        sent_any = True
                                    except Exception as e:
                                        logger.error(f"Fehler beim Senden der globalen Benachrichtigung '{alias}': {e}")
                                    
                            # 2. Server-spezifische Benachrichtigung
                            if device.webhook_url:
                                try:
                                    logger.info(f"Sende UP-Benachrichtigung an spezifischen Webhook für {device_name}")
                                    spec_notifier = TeamsNotifier(device.webhook_url)
                                    await spec_notifier.send_device_up(
                                        device_name=device_name,
                                        check_type=successful_checks[0]["type"] if successful_checks else "unknown"
                                    )
                                    sent_any = True
                                except Exception as e:
                                    logger.error(f"Fehler beim Senden der spezifischen Benachrichtigung: {e}")
                                    
                            if sent_any:
                                device.last_notification_time = device.last_check_time"""

content = content.replace(old_up_notif, new_up_notif)


# 4. Remove teams_notifier from lifespan
old_lifespan = """    # Teams Notifier initialisieren
    webhook_url = userdata.get("teams_webhook_url", "")
    teams_notifier = TeamsNotifier(webhook_url)"""

new_lifespan = """    # Teams Notifier wird jetzt bei Bedarf direkt instanziiert
    pass"""

content = content.replace(old_lifespan, new_lifespan)

# 5. Fix APIs: AddDeviceRequest, UpdateDeviceRequest
old_api_models = """class AddDeviceRequest(BaseModel):
    name: str
    host: str
    ports: List[int]
    webhook_url: Optional[str] = None
    use_global_webhook: bool = True
    notifications_enabled: bool = True
    ping_enabled: bool = True


@app.post("/api/devices")
async def add_device(request: AddDeviceRequest) -> Dict[str, Any]:
    \"\"\"Fügt ein neues Gerät zur Überwachung hinzu\"\"\"
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
    }"""

new_api_models = """class AddDeviceRequest(BaseModel):
    name: str
    host: str
    ports: List[int]
    webhook_url: Optional[str] = None
    global_webhooks: List[str] = []
    notifications_enabled: bool = True
    ping_enabled: bool = True


@app.post("/api/devices")
async def add_device(request: AddDeviceRequest) -> Dict[str, Any]:
    \"\"\"Fügt ein neues Gerät zur Überwachung hinzu\"\"\"
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
        "global_webhooks": request.global_webhooks
    }"""

content = content.replace(old_api_models, new_api_models)

# 6. Fix Add API DeviceMonitor instantiation
old_add_monitor = """            new_monitor = DeviceMonitor(
                request.name, 
                checks, 
                new_device_config["notifications_enabled"],
                new_device_config["webhook_url"],
                new_device_config["use_global_webhook"]
            )"""

new_add_monitor = """            new_monitor = DeviceMonitor(
                request.name, 
                checks, 
                new_device_config["notifications_enabled"],
                new_device_config["webhook_url"],
                new_device_config["global_webhooks"]
            )"""

content = content.replace(old_add_monitor, new_add_monitor)

# 7. UpdateDeviceRequest
old_update_device = """class UpdateDeviceRequest(BaseModel):
    new_name: Optional[str] = None
    host: str
    ports: List[int]
    notifications_enabled: bool
    use_global_webhook: bool = True
    webhook_url: Optional[str] = None
    ping_enabled: bool = True


@app.put("/api/devices/{device_name}")
async def update_device(device_name: str, request: UpdateDeviceRequest) -> Dict[str, Any]:
    \"\"\"Aktualisiert ein bestehendes Gerät\"\"\"
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
    device_config["use_global_webhook"] = request.use_global_webhook"""

new_update_device = """class UpdateDeviceRequest(BaseModel):
    new_name: Optional[str] = None
    host: str
    ports: List[int]
    notifications_enabled: bool
    global_webhooks: List[str] = []
    webhook_url: Optional[str] = None
    ping_enabled: bool = True


@app.put("/api/devices/{device_name}")
async def update_device(device_name: str, request: UpdateDeviceRequest) -> Dict[str, Any]:
    \"\"\"Aktualisiert ein bestehendes Gerät\"\"\"
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
    device_config["global_webhooks"] = request.global_webhooks"""

content = content.replace(old_update_device, new_update_device)

# 8. Update API DeviceMonitor instantiation
old_update_monitor = """        new_monitor = DeviceMonitor(
            target_name, 
            checks, 
            request.notifications_enabled,
            request.webhook_url
        )"""

new_update_monitor = """        new_monitor = DeviceMonitor(
            target_name, 
            checks, 
            request.notifications_enabled,
            request.webhook_url,
            request.global_webhooks
        )"""

content = content.replace(old_update_monitor, new_update_monitor)


# 9. Settings
old_settings = """class SettingsRequest(BaseModel):
    teams_webhook_url: str


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    \"\"\"Gibt die globalen Einstellungen zurück\"\"\"
    return {
        "teams_webhook_url": userdata.get("teams_webhook_url", "")
    }


@app.post("/api/settings")
async def save_settings(request: SettingsRequest) -> Dict[str, Any]:
    \"\"\"Speichert die globalen Einstellungen\"\"\"
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
    \"\"\"Sendet eine Test-Nachricht an den Webhook\"\"\"
    global teams_notifier
    
    success = await teams_notifier.send_test_notification(request.teams_webhook_url)"""

new_settings = """class GlobalWebhook(BaseModel):
    alias: str
    url: str

class SettingsRequest(BaseModel):
    global_webhooks: List[GlobalWebhook]
    
class TestWebhookRequest(BaseModel):
    url: str


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    \"\"\"Gibt die globalen Einstellungen zurück\"\"\"
    return {
        "global_webhooks": userdata.get("global_webhooks", [])
    }


@app.post("/api/settings")
async def save_settings(request: SettingsRequest) -> Dict[str, Any]:
    \"\"\"Speichert die globalen Einstellungen\"\"\"
    global userdata
    
    # Konvertieren der GlobalWebhook Objekte in dicts
    userdata["global_webhooks"] = [{"alias": w.alias, "url": w.url} for w in request.global_webhooks]
    
    try:
        save_userdata(userdata)
        
        return {"status": "success", "message": "Settings saved"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings/test-webhook")
async def test_webhook(request: TestWebhookRequest) -> Dict[str, Any]:
    \"\"\"Sendet eine Test-Nachricht an den Webhook\"\"\"
    temp_notifier = TeamsNotifier(request.url)
    success = await temp_notifier.send_test_notification(request.url)"""

content = content.replace(old_settings, new_settings)

with open("api.py", "w", encoding="utf-8") as f:
    f.write(content)
