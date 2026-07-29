import argparse
import asyncio
import os

from .assistant import Athena
from .langgraph_agent import LangGraphAthena, LangGraphUnavailable, format_failure
from .speech import create_speaker
from .storage import Storage
from .tools import build_tools


async def run(args: argparse.Namespace) -> None:
    parser = argparse.ArgumentParser(description="Athena personal assistant")
    parser.add_argument("--text-only", action="store_true", help="disable spoken responses")
    parser.add_argument("--langgraph", action="store_true", help="use the LangChain/LangGraph MCP agent")
    parser.add_argument("--allow-writes", action="store_true", help="allow write-capable MCP tools in LangGraph mode")
    parser.add_argument("--model", help="Ollama model name, for example llama3.2:latest")
    args = parser.parse_args()
    assistant = Athena(build_tools(Storage())) if not args.langgraph else None
    configured_model = args.model or os.getenv("ATHENA_LLM_MODEL", "llama3.2:latest")
    configured_model = configured_model.strip().strip('"').strip("'") or "llama3.2:latest"
    graph_assistant = LangGraphAthena(configured_model, args.allow_writes) if args.langgraph else None
    if graph_assistant is not None:
        print(f"Athena online using Ollama model: {configured_model}")
    speaker = create_speaker(args.text_only)
    print("Athena online. Type ‘help’ for commands, or ‘quit’ to exit.")
    while True:
        try:
            text = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nAthena offline.")
            return
        lowered = text.strip().lower()
        if lowered in {"new chat", "clear chat", "reset conversation"} and graph_assistant is not None:
            graph_assistant.reset()
            response = "Conversation cleared. I’m ready for a new request."
            print(f"Athena: {response}")
            speaker.speak(response)
            continue
        if graph_assistant is not None:
            try:
                response = await graph_assistant.ask(text)
            except LangGraphUnavailable as exc:
                response = f"LangGraph is not ready: {exc}"
            except BaseException as exc:
                response = f"The LangGraph request failed safely: {format_failure(exc)}"
        else:
            response = assistant.handle(text)
        print(f"Athena: {response}")
        speaker.speak(response)
        if lowered in {"quit", "exit", "goodbye"}:
            return


def main() -> None:
    parser = argparse.ArgumentParser(description="Athena personal assistant")
    parser.add_argument("--text-only", action="store_true", help="disable spoken responses")
    parser.add_argument("--langgraph", action="store_true", help="use the LangChain/LangGraph MCP agent")
    parser.add_argument("--allow-writes", action="store_true", help="allow write-capable MCP tools in LangGraph mode")
    parser.add_argument("--model", help="Ollama model name, for example llama3.2:latest")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
