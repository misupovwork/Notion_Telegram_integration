import os
import httpx
from fastapi import FastAPI
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.requests import Request

app = FastAPI()
mcp = Server("telegram-mcp")
BOT_TOKEN = os.getenv("8028026569:AAGqCGSXgOgLe8-vaeyDPPRpF55LXHDEvu4")

@mcp.tool()
async def send_telegram_message(chat_id: str, message: str) -> str:
    """Send a text message to a specific Telegram chat ID."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"chat_id": chat_id, "text": message})
        if resp.status_code == 200:
            return "Message sent successfully to Telegram."
        return f"Failed to send message: {resp.text}"

# Set up SSE (Server-Sent Events) so Notion can communicate over the web
transport = SseServerTransport("/messages")

@app.get("/sse")
async def sse_endpoint(request: Request):
    return await transport.handle_sse(request)

@app.post("/messages")
async def messages_endpoint(request: Request):
    return await transport.handle_post_message(request)
