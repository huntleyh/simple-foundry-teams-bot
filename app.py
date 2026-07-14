from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext, MessageFactory
from botbuilder.schema import Activity
import traceback
from dotenv import load_dotenv
load_dotenv()

from config import APP_ID, APP_PASSWORD, PORT
from bot import FoundryAgentBot

SETTINGS = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
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
        await turn_context.send_activity(MessageFactory.text(text))

    sent = 0
    for ref in refs:
        await ADAPTER.continue_conversation(ref, _send, APP_ID)
        sent += 1

    return web.json_response({"sent": sent})


APP = web.Application()
APP.router.add_post("/api/messages", messages)
APP.router.add_post("/api/proactive", proactive)

if __name__ == "__main__":
    print(f"Bot running on http://localhost:{PORT}/api/messages")
    web.run_app(APP, host="localhost", port=PORT)
