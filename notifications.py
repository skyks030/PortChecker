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
            logger.debug(f"Benachrichtigung übersprungen (nicht konfiguriert): {device_name} - {message}")
            return False
        
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
                                        "title": "Gerät:",
                                        "value": device_name
                                    },
                                    {
                                        "title": "Status:",
                                        "value": status
                                    },
                                    {
                                        "title": "Check-Typ:",
                                        "value": check_type.upper()
                                    },
                                    {
                                        "title": "Zeit:",
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
                    if response.status == 200:
                        logger.info(f"Teams Benachrichtigung gesendet: {device_name} - {status}")
                        return True
                    else:
                        logger.error(
                            f"Teams Benachrichtigung fehlgeschlagen: "
                            f"Status {response.status}, {await response.text()}"
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
            message=f"❌ {device_name} ist nicht erreichbar!",
            details=f"Fehler: {error}"
        )
    
    async def send_device_up(self, device_name: str, check_type: str):
        """Sendet Benachrichtigung für wiederhergestelltes Gerät"""
        await self.send_alert(
            device_name=device_name,
            check_type=check_type,
            status="UP",
            message=f"✅ {device_name} ist wieder erreichbar!",
            details="Das Gerät antwortet wieder normal."
        )
