# Local Testing: simple-teams-bot → ADK Agent → Foundry

## Architecture

```
agentsplayground
    ↓  Bot Framework Activity (port 3978)
simple-teams-bot  (bot.py / app.py)
    ↓  POST /responses  (OpenAI Responses protocol)
app_server.py  OR  Foundry Hosted Agent endpoint
    ↓  DefaultAzureCredential → managed identity token
aifoundry9263.openai.azure.com  (gpt-4.1, private endpoint)
```

---

## Local Test (no Azure deployment needed)

### Terminal 1 — ADK agent server
```powershell
cd C:\Temp\adk-agent
python app_server.py
# Listening on http://0.0.0.0:8088
```

### Terminal 2 — Teams bot
```powershell
cd C:\Temp\simple-teams-bot
$env:AGENT_ENDPOINT = "http://localhost:8088/responses"
.venv\Scripts\python app.py
# Bot on http://localhost:3978/api/messages
```

> The bot auto-detects `http://localhost` and skips auth. For any other URL it
> acquires a token via `DefaultAzureCredential` (your active `az login` session).

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
$env:AGENT_ENDPOINT = "https://aifoundry9263.services.ai.azure.com/api/projects/agent-project/agents/greeting-agent/endpoint/protocols/openai/responses"
.venv\Scripts\python app.py
```

Then test with the Agents Playground as above, or call the Responses endpoint directly:
```powershell
$TOKEN = (az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv)
$BASE  = "https://aifoundry9263.services.ai.azure.com/api/projects/agent-project"
curl -X POST "$BASE/agents/greeting-agent/endpoint/protocols/openai/responses?api-version=v1" `
     -H "Authorization: Bearer $TOKEN" `
     -H "Content-Type: application/json" `
     -d '{"input":"hello!","stream":false}'
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
