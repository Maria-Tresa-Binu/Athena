"""Web host for Athena's mobile-friendly browser client."""

import argparse
import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .langgraph_agent import LangGraphAthena, LangGraphUnavailable, format_failure

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
app = FastAPI(title="Athena")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
assistant: LangGraphAthena | None = None
assistant_lock = asyncio.Lock()


class ChatRequest(BaseModel):
    message: str


def get_assistant() -> LangGraphAthena:
    global assistant
    if assistant is None:
        assistant = LangGraphAthena()
    return assistant


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/static/{asset:path}")
async def static_asset(asset: str) -> FileResponse:
    path = (WEB_ROOT / asset).resolve()
    if WEB_ROOT not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(path)


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    async with assistant_lock:
        try:
            response = await get_assistant().ask(message)
        except LangGraphUnavailable as exc:
            response = f"Athena is not ready: {exc}"
        except BaseException as exc:
            response = f"Athena failed safely: {format_failure(exc)}"
    return {"response": response}


@app.post("/api/briefing")
async def briefing() -> dict[str, Any]:
    prompt = (
        "Prepare my Athena activation briefing. Use connected MCP tools to fetch current data: "
        "(1) the exact number of unread Gmail messages, if Gmail is authorized; "
        "(2) today's Google Calendar events and task-like items, if Calendar is authorized; "
        "and (3) the latest technology news with titles and sources. "
        "Return a concise response with sections EMAIL, CALENDAR, and NEWS. "
        "Clearly say when a connector is not authorized. Never invent counts, events, or stories."
    )
    async with assistant_lock:
        try:
            response = await get_assistant().ask(prompt)
        except LangGraphUnavailable as exc:
            response = f"Athena is not ready: {exc}"
        except BaseException as exc:
            response = f"Athena failed safely: {format_failure(exc)}"
    return {"response": response}


@app.post("/api/reset")
async def reset() -> dict[str, str]:
    get_assistant().reset()
    return {"response": "Conversation cleared."}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Athena's web app")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
