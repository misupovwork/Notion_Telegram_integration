import os
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount, Route
from starlette.applications import Starlette

# 1. Initialize FastMCP (Handles complex protocol bridging automatically)
mcp = FastMCP("Telegram & Notion Bot")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")


# 2. Define the Telegram tool cleanly via a decorator
@mcp.tool()
async def send_telegram_message(chat_id: str, message: str) -> str:
    """Send a text message to a specific Telegram chat ID."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"chat_id": chat_id, "text": message})
        if resp.status_code == 200:
            return "Message sent successfully to Telegram."
        else:
            return f"Failed to send message: {resp.text}"


# 3. NEW: Define the Notion Database Editing Tool
@mcp.tool()
async def rename_notion_database(database_id: str, new_name: str) -> str:
    """Edit the title of a Notion database."""
    if not NOTION_API_KEY:
        return "Error: NOTION_API_KEY environment variable is not set on the server."

    url = f"https://api.notion.com/v1/databases/{database_id}"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    payload = {
        "title": [
            {
                "text": {
                    "content": new_name
                }
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        resp = await client.patch(url, headers=headers, json=payload)
        if resp.status_code == 200:
            return f"Database successfully renamed to '{new_name}'."
        else:
            return f"Failed to rename database: {resp.status_code} - {resp.text}"


# 4. Setup the SSE Transport bridge
transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    """Bridge standard requests to the raw MCP SSE connection."""
    async with transport.connect_sse(
            request.scope, request.receive, request._send
    ) as (in_stream, out_stream):
        await mcp._mcp_server.run(
            in_stream, out_stream, mcp._mcp_server.create_initialization_options()
        )


# 5. Create a dedicated routing app strictly for the streams
sse_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages/", app=transport.handle_post_message),
    ]
)

# 6. Build the main FastAPI app
app = FastAPI()

# VERY IMPORTANT: CORS explicitly allows Notion's domains and Auth Headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the streams securely to the root of FastAPI
app.mount("/", sse_app)


@app.get("/health")
def health_check():
    """Cloud Run Health Check"""
    return {"status": "ok", "message": "Server is live!"}
