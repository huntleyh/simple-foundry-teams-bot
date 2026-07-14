# Local Testing: simple-teams-bot → ADK Agent → Foundry

## Architecture

```
agentsplayground
    ↓  Bot Framework Activity (port 3978)
simple-teams-bot  (bot.py / app.py)
    ↓  POST /responses  (OpenAI Responses protocol)
app_server.py  OR  Foundry Hosted Agent endpoint
    ↓  DefaultAzureCredential → az login (local) or managed identity (Foundry)
aifoundry9263.openai.azure.com  (gpt-4.1, public endpoint)
```

---

## Local Test (calls the public Foundry endpoint via `az login`)

> **Pre-requisite**: `az login` must be active — the local agent server calls
> `https://aifoundry9263.openai.azure.com/` using your CLI credentials.

### Terminal 1 — ADK agent server
```powershell
cd C:\Temp\adk-agent
$env:AZURE_API_BASE = "https://aifoundry9263.openai.azure.com/"
$env:AZURE_API_VERSION = "2024-12-01-preview"
$env:AZURE_DEPLOYMENT_NAME = "gpt-4.1"
$env:PYTHONUTF8 = "1"
.venv\Scripts\python app_server.py
# Listening on http://0.0.0.0:8088
```

### Terminal 2 — Teams bot
```powershell
cd C:\Temp\simple-teams-bot
# Edit .env and set: AGENT_ENDPOINT=http://localhost:8088/responses
notepad .env
.venv\Scripts\python app.py
# Bot on http://localhost:3978/api/messages
```

> The bot reads `AGENT_ENDPOINT` from `.env` via python-dotenv.
> Switch between local and deployed by editing that one line.

### Terminal 3 — Agents Playground
```powershell
agentsplayground -e "http://localhost:3978/api/messages"
```

> Adjust the port if `app.py` uses a different `PORT` env var (e.g. 3958).

---

## Deployed Foundry Hosted Agent

### Redeploy image after code changes
```powershell
cd C:\Temp\adk-agent

# Use a versioned tag so Foundry detects the new image and creates a new version
$tag = "greeting-agent:$(Get-Date -Format 'yyyyMMdd-HHmm')"
$env:NO_COLOR = "1"; chcp 65001 | Out-Null
az acr build --registry acragentfzu5sn --image $tag --file Dockerfile .

# Deploy (creates a new version; roles are NOT re-assigned — they persist on the stable identity)
python deploy.py --image $tag
```

> **Never delete the agent** — deleting creates a new `instance_identity` and forces role re-assignment.
> Just create new versions. The identity (and its roles) persist across all versions.

### One-time role setup (first deployment only, or after accidental deletion)
```powershell
python deploy.py --grant-roles
```

### Start bot pointing at Foundry
```powershell
cd C:\Temp\simple-teams-bot
# .env already has AGENT_ENDPOINT set to the deployed Foundry endpoint (default)
# Verify or edit:
notepad .env
.venv\Scripts\python app.py
```

Then test with the Agents Playground as above, or call the Responses endpoint directly:
```powershell
$TOKEN = (az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv)
$BASE  = "https://aifoundry9263.services.ai.azure.com/api/projects/agent-project"
curl -X POST "$BASE/agents/greeting-agent/endpoint/protocols/openai/responses?api-version=v1" `
     -H "Authorization: Bearer $TOKEN" `
     -H "Content-Type: application/json" `
     -d '{"input":"hello!","stream":false,"store":true}'
```

Or via the Python SDK (use the adk-agent venv which has `azure-ai-projects`):
```powershell
cd C:\Temp\adk-agent
.venv\Scripts\python deploy.py --invoke "hello!"
```

---

## Teams Sideload (test in Microsoft Teams)

### Prerequisites
- An Azure Bot Service registration with the Teams channel enabled  
  (`foundry-greeting-bot` in `rg-aifoundry9263`, App ID `1b82177f-70cb-4eb9-8ab0-1d4a9b015d98`)
- A running dev tunnel forwarding port 3978 to the bot (see below)

### 1 — Start the dev tunnel
```powershell
devtunnel host foundry-bot
# Tunnel URL: https://mx0fnjk2-3978.use.devtunnels.ms  → localhost:3978
```

> The tunnel must be running **before** you start the bot so Teams can reach it.

### 2 — Update the bot endpoint if the tunnel URL changed
```powershell
az bot update `
  --resource-group rg-aifoundry9263 `
  --name foundry-greeting-bot `
  --endpoint "https://<tunnel-url>/api/messages"
```

### 3 — Start the bot
```powershell
cd C:\Temp\simple-teams-bot
# .env already points AGENT_ENDPOINT at the deployed Foundry endpoint
.venv\Scripts\python app.py
```

### 4 — Package the Teams app
```powershell
cd C:\Temp\simple-teams-bot\teamsapp
.\package.ps1
# Produces: foundry-greeting.zip
```

### 5 — Sideload in Teams
1. Open Teams → **Apps** → **Manage your apps** → **Upload an app**
2. Select `foundry-greeting.zip`
3. Start a chat with **Foundry Greeting Bot**

> **Troubleshooting**  
> - *"Please make sure the bot is registered and teams' channel is enabled"* → run `az bot msteams create --resource-group rg-aifoundry9263 --name foundry-greeting-bot`  
> - *`KeyError: 'access_token'`* → `MicrosoftAppTenantId` is missing from `.env` or not passed as `channel_auth_tenant` in `BotFrameworkAdapterSettings`

### Proactive messaging
```powershell
# After at least one user has messaged the bot (to register their conversation reference):
curl -X POST http://localhost:3978/api/proactive `
     -H "Content-Type: application/json" `
     -d '{"message": "Hello from the server!"}'
```

---

## Key files

| File | Purpose |
|------|---------|
| `C:\Temp\adk-agent\greeting_agent\agent.py` | ADK agent definition (unchanged) |
| `C:\Temp\adk-agent\app_server.py` | Foundry Responses protocol wrapper (port 8088) |
| `C:\Temp\adk-agent\Dockerfile` | Container image (exposes 8088) |
| `C:\Temp\adk-agent\deploy.py` | Deploy/invoke via Python SDK |
| `C:\Temp\adk-agent\azure.yaml` | azd manifest for Foundry Hosted Agent |
| `C:\Temp\simple-teams-bot\bot.py` | Bot Framework bot — bridges Activity → Responses |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ENDPOINT` | `http://localhost:8088/responses` | Responses endpoint the bot calls |
| `FOUNDRY_API_KEY` | *(unset)* | API key for the deployed Foundry endpoint — takes priority over Entra token |
| `MicrosoftAppId` | *(required)* | Bot App registration client ID |
| `MicrosoftAppPassword` | *(required)* | Bot App registration client secret |
| `MicrosoftAppTenantId` | *(required for SingleTenant bots)* | Tenant ID — sets the correct OAuth token endpoint |
| `PORT` | `3978` | Port the Bot Framework server listens on |
| `AZURE_API_BASE` | *(set in .env or azure.yaml)* | Azure OpenAI endpoint for the ADK agent |
| `AZURE_DEPLOYMENT_NAME` | `gpt-4.1` | Model deployment name |

## Infrastructure resources (rg-aifoundry9263)

| Resource | Name |
|----------|------|
| AI Foundry account | `aifoundry9263` |
| AI project | `agent-project` |
| Container Registry | `acragentfzu5sn` |
| Bastion | `bas-aifoundry9263` |
| Jump box VM | `vm-jumpbox-aifoundry9263` (192.168.4.4) |
| SSH alias | `ssh privatefoundry` |
