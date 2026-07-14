from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext
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


APP = web.Application()
APP.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    print(f"Bot running on http://localhost:{PORT}/api/messages")
    web.run_app(APP, host="localhost", port=PORT)
