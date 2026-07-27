import argparse
import asyncio
import os

from .assistant import Athena
from .langgraph_agent import LangGraphAthena, LangGraphUnavailable
from .speech import create_speaker
from .storage import Storage
from .tools import build_tools


def main() -> None:
    parser = argparse.ArgumentParser(description="Athena personal assistant")
    parser.add_argument("--text-only", action="store_true", help="disable spoken responses")
    parser.add_argument("--langgraph", action="store_true", help="use the LangChain/LangGraph MCP agent")
    parser.add_argument("--allow-writes", action="store_true", help="allow write-capable MCP tools in LangGraph mode")
    args = parser.parse_args()
    assistant = Athena(build_tools(Storage())) if not args.langgraph else None
    graph_assistant = LangGraphAthena(os.getenv("ATHENA_LLM_MODEL", "openai:gpt-4o-mini"), args.allow_writes) if args.langgraph else None
    speaker = create_speaker(args.text_only)
    print("Athena online. Type ‘help’ for commands, or ‘quit’ to exit.")
    while True:
        try:
            text = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nAthena offline.")
            return
        if graph_assistant is not None:
            try:
                response = asyncio.run(graph_assistant.ask(text))
            except LangGraphUnavailable as exc:
                response = f"LangGraph is not ready: {exc}"
            except Exception as exc:
                response = f"The LangGraph request failed safely: {exc}"
        else:
            response = assistant.handle(text)
        print(f"Athena: {response}")
        speaker.speak(response)
        if text.strip().lower() in {"quit", "exit", "goodbye"}:
            return


if __name__ == "__main__":
    main()
