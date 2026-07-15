from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext, MessageFactory, CardFactory
from botbuilder.schema import Activity
import os
import traceback
from dotenv import load_dotenv
load_dotenv()

from config import APP_ID, APP_PASSWORD, APP_TENANT_ID, PORT
from bot import FoundryAgentBot

SETTINGS = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD, channel_auth_tenant=APP_TENANT_ID)
ADAPTER = BotFrameworkAdapter(SETTINGS)
BOT = FoundryAgentBot()


async def on_error(context: TurnContext, error: Exception):
    print(f"\n[on_turn_error]: {error}")
    traceback.print_exc()
    await context.send_activity("The bot encountered an error.")


ADAPTER.on_turn_error = on_error


async def messages(req: web.Request) -> web.Response:
    if req.content_type != "application/json":
        return web.Response(status=415)

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return web.json_response(data=response.body, status=response.status)
    return web.Response(status=201)


async def proactive(req: web.Request) -> web.Response:
    """POST /api/proactive
    Send a proactive message to one or all known conversations.

    Body (JSON):
      { "message": "Hello!", "user_id": "optional — channel_id:user_id key" }

    If user_id is omitted, the message is broadcast to all stored conversations.

    Note: no authentication on this endpoint — add a shared secret header check
    before exposing it publicly.
    """
    from bot import conversation_references

    body = await req.json()
    text = body.get("message", "").strip()
    if not text:
        return web.json_response({"error": "message is required"}, status=400)

    user_id = body.get("user_id")
    refs = (
        [conversation_references[user_id]]
        if user_id and user_id in conversation_references
        else list(conversation_references.values())
    )

    if not refs:
        return web.json_response({"error": "no conversations stored yet — a user must message the bot first"}, status=404)

    async def _send(turn_context: TurnContext):
        from cards import agent_reply_card
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.adaptive_card(agent_reply_card(text)))
        )

    # continue_conversation requires a non-empty bot_id or a ClaimsIdentity.
    # When running locally with no credentials, supply an anonymous identity with
    # explicit empty-string claims so the connector uses anonymous (no-token) mode.
    if APP_ID:
        continue_kwargs = {"bot_id": APP_ID}
    else:
        from botframework.connector.auth import ClaimsIdentity
        continue_kwargs = {
            "claims_identity": ClaimsIdentity(
                claims={"aud": "", "appid": ""},
                is_authenticated=True,
            )
        }

    sent = 0
    errors: list[str] = []
    for ref in refs:
        try:
            await ADAPTER.continue_conversation(ref, _send, **continue_kwargs)
            sent += 1
        except Exception as exc:
            print(f"[proactive] delivery error: {exc}")
            traceback.print_exc()
            errors.append(str(exc))

    result: dict = {"sent": sent}
    if errors:
        result["errors"] = errors
    return web.json_response(result, status=200 if sent else 500)


APP = web.Application()
APP.router.add_post("/api/messages", messages)
APP.router.add_post("/api/proactive", proactive)

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Bot running on http://{host}:{PORT}/api/messages")
    web.run_app(APP, host=host, port=PORT)
