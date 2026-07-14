import os

APP_ID = os.environ.get("MicrosoftAppId", "")
APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
APP_TENANT_ID = os.environ.get("MicrosoftAppTenantId", "")
PORT = int(os.environ.get("PORT", 3978))
