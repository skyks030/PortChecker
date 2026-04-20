import asyncio
from api import load_userdata, save_userdata, userdata
import yaml
import os

if os.path.exists("data/userdata.yaml"):
    os.remove("data/userdata.yaml")

with open("config.yaml", "w", encoding="utf-8") as f:
    yaml.dump({
        "teams_webhook_url": "https://old.url",
        "devices": [
            {
                "name": "TestDevice",
                "use_global_webhook": True,
                "webhook_url": None,
                "checks": []
            }
        ]
    }, f)

data = load_userdata()
assert data["global_webhooks"][0]["alias"] == "Default"
assert data["global_webhooks"][0]["url"] == "https://old.url"
assert "Default" in data["devices"][0]["global_webhooks"]
assert "use_global_webhook" not in data["devices"][0]

print("Python Backend APIs parsing and migration OK")

