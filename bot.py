import os
import aiohttp
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory

# Keyed by channel_id:user_id — populated whenever a user sends a message.
# Used by the POST /api/proactive endpoint to send unprompted messages.
conversation_references: dict[str, object] = {}


AGENT_ENDPOINT = os.environ.get(
    "AGENT_ENDPOINT",
    "http://localhost:8088/responses",
)

# Per-user session tracking: maps (channel, user_id) -> previous_response_id
# so multi-turn history threads correctly through the Responses protocol.
_response_ids: dict[str, str] = {}


class FoundryAgentBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        # Persist reference so /api/proactive can reach this conversation later
        from botbuilder.core import TurnContext as TC
        key = f"{turn_context.activity.channel_id}:{turn_context.activity.from_property.id}"
        conversation_references[key] = TC.get_conversation_reference(turn_context.activity)

        user_text = turn_context.activity.text or ""
        session_key = f"{turn_context.activity.channel_id}:{turn_context.activity.from_property.id}"

        reply, response_id = await _call_responses(user_text, _response_ids.get(session_key))
        if response_id:
            _response_ids[session_key] = response_id   # thread subsequent turns

        await turn_context.send_activity(MessageFactory.text(reply))

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello! Ask me anything.")


async def _call_responses(message: str, previous_response_id: str | None) -> tuple[str, str | None]:
    """POST to the Responses protocol endpoint and return (text, response_id).

    Works against both the local app_server.py (no auth) and the deployed
    Foundry Hosted Agent (bearer token via DefaultAzureCredential).
    """
    headers = {"Content-Type": "application/json"}

    if not AGENT_ENDPOINT.startswith("http://localhost"):
        # Deployed Foundry endpoint requires authentication.
        # Priority: FOUNDRY_API_KEY env var → DefaultAzureCredential (Entra token).
        api_key = os.environ.get("FOUNDRY_API_KEY")
        if api_key:
            headers["api-key"] = api_key
        else:
            from azure.identity.aio import DefaultAzureCredential
            async with DefaultAzureCredential() as cred:
                token = await cred.get_token("https://ai.azure.com/.default")
            headers["Authorization"] = f"Bearer {token.token}"

    payload: dict = {"input": message, "stream": False, "store": True}
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    # api-version=v1 is required for the Foundry Hosted Agent Responses endpoint
    url = AGENT_ENDPOINT
    if not url.startswith("http://localhost"):
        url = f"{url}?api-version=v1"

    async with aiohttp.ClientSession() as http:
        async with http.post(url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()

    # Extract plain text from the OpenAI Responses object
    text = _extract_text(data)
    return text, data.get("id")  # id becomes next turn's previous_response_id


def _extract_text(data: dict) -> str:
    for item in data.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return part.get("text", "")
    return data.get("output_text") or str(data)
