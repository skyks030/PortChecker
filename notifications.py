"""
Microsoft Teams Benachrichtigungs-Modul
Sendet formatierte Adaptive Cards an Teams Channel
"""

import aiohttp
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class TeamsNotifier:
    """Verwaltet Microsoft Teams Benachrichtigungen"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url and not webhook_url.startswith("https://your-"))
        
        if not self.enabled:
            logger.warning("Teams Webhook URL nicht konfiguriert - Benachrichtigungen deaktiviert")
    
    async def send_alert(
        self,
        device_name: str,
        check_type: str,
        status: str,
        message: str,
        details: Optional[str] = None
    ) -> bool:
        """
        Sendet eine Benachrichtigung an Teams
        
        Args:
            device_name: Name des Geräts
            check_type: Art der Prüfung (ping, http, port)
            status: Status (DOWN, UP, WARNING)
            message: Hauptnachricht
            details: Zusätzliche Details (optional)
        
        Returns:
            True wenn erfolgreich gesendet, sonst False
        """
        if not self.enabled:
            logger.warning(f"Benachrichtigung für {device_name} KANN NICHT gesendet werden: Webhook URL fehlt oder ungültig.")
            return False
            
        logger.info(f"Sende Teams Alert für {device_name} (Status: {status})...")
        
        # Farbe basierend auf Status
        color = {
            "DOWN": "Attention",  # Rot
            "UP": "Good",         # Grün
            "WARNING": "Warning"  # Gelb
        }.get(status, "Default")
        
        # Adaptive Card erstellen
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"🔔 Network Monitor Alert",
                                "weight": "Bolder",
                                "size": "Large"
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {
                                        "title": "Device:",
                                        "value": device_name
                                    },
                                    {
                                        "title": "Status:",
                                        "value": status
                                    },
                                    {
                                        "title": "Check Type:",
                                        "value": check_type.upper()
                                    },
                                    {
                                        "title": "Time:",
                                        "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": message,
                                "wrap": True,
                                "weight": "Bolder",
                                "color": color
                            }
                        ]
                    }
                }
            ]
        }
        
        # Details hinzufügen falls vorhanden
        if details:
            card["attachments"][0]["content"]["body"].append({
                "type": "TextBlock",
                "text": details,
                "wrap": True,
                "isSubtle": True
            })
        
        # An Teams senden
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=card,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_text = await response.text()
                    if 200 <= response.status < 300:
                        logger.info(f"Teams Benachrichtigung erfolgreich gesendet: {device_name} - {status} (Status: {response.status})")
                        return True
                    else:
                        logger.error(
                            f"Teams Benachrichtigung fehlgeschlagen: "
                            f"Status {response.status}, Body: {response_text}"
                        )
                        return False
        except Exception as e:
            logger.error(f"Fehler beim Senden der Teams Benachrichtigung: {e}")
            return False
    
    async def send_device_down(self, device_name: str, check_type: str, error: str):
        """Sendet Benachrichtigung für ausgefallenes Gerät"""
        await self.send_alert(
            device_name=device_name,
            check_type=check_type,
            status="DOWN",
            message=f"❌ {device_name} is unreachable!",
            details=f"Error: {error}"
        )
    
    async def send_device_up(self, device_name: str, check_type: str):
        """Sendet Benachrichtigung für wiederhergestelltes Gerät"""
        await self.send_alert(
            device_name=device_name,
            check_type=check_type,
            status="UP",
            message=f"✅ {device_name} is reachable again!",
            details="The device is responding normally again."
        )

    async def send_test_notification(self, webhook_url: Optional[str] = None) -> bool:
        """Sendet eine Test-Benachrichtigung"""
        # Verwende temporäre URL wenn angegeben, sonst gespeicherte
        original_url = self.webhook_url
        if webhook_url:
            self.webhook_url = webhook_url
            self.enabled = True # Temporarily enable for test
            
        try:
            return await self.send_alert(
                device_name="Test-System",
                check_type="SYSTEM",
                status="WARNING",
                message="🧪 This is a test notification",
                details="If you see this message, the webhook integration is working!"
            )
        finally:
            if webhook_url:
                self.webhook_url = original_url
                self.enabled = bool(original_url)
