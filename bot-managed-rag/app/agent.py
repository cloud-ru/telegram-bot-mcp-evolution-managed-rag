from __future__ import annotations

from typing import Any
from pathlib import Path
from loguru import logger

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_gigachat import GigaChat

from .mcp_client import McpClient


def load_system_prompt() -> str:
    default = (
        "Ты — Telegram-ассистент. Используй инструмент request_to_rag для получения релевантного контента. "
        "Отвечай кратко и по-делу, на русском языке. Если инструмент вернул источники, аккуратно их перечисли."
    )
    p = Path(__file__).with_name("system_prompt.txt")
    try:
        text = p.read_text(encoding="utf-8").strip()
        return text or default
    except FileNotFoundError:
        return default


def build_agent(
    mcp: McpClient,
    rag_tool_name: str,
    model_name: str,
    temperature: float,
    scope: str,
    credentials: str | None,
    verify_ssl: bool = True,
):
    """Create a LangGraph ReAct agent that can call the MCP RAG tool via URL.

    The agent uses GigaChat as the LLM and exposes a single tool which proxies
    to the remote MCP server tool that implements RAG.
    """

    tool_invoked = False

    # Define a LangChain tool that delegates to MCP
    @tool("request_to_rag", return_direct=False)
    async def request_to_rag(query: str) -> str:
        """Инструмент обращается к API Базы Знаний и получает релевантные документы по запросу пользователя. На выходе выдает релевантные документы, которые нужно использовать для ответа на вопрос пользователя."""
        nonlocal tool_invoked
        tool_invoked = True
        logger.info(f"MCP tool '{rag_tool_name}' invoked with query: {query!r}")
        try:
            result = await mcp.call_tool_text(name=rag_tool_name, arguments={"query": query})
            logger.info(f"MCP tool '{rag_tool_name}' response: {result[:25]!r}")
            return result
        except Exception as e:
            logger.exception(f"MCP tool '{rag_tool_name}' failed for query {query!r}: {e}")
            raise

    # Initialize GigaChat LLM
    llm = GigaChat(
        streaming=True,
        temperature=temperature,
        model=model_name,
        scope=scope,
        credentials=credentials,
        verify_ssl_certs=False,
    )

    # Load system prompt from external file for easy editing
    system_prompt = load_system_prompt()

    agent = create_react_agent(
        model=llm,
        tools=[request_to_rag],
        prompt=system_prompt,
    )

    async def astream_answer(user_text: str):
        """Stream answer tokens produced by the agent while it reasons and answers.

        Yields incremental text chunks for UI streaming.
        """
        logger.info(f"Agent started for user text: {user_text!r}")
        # We stream events and capture model token stream after tool execution
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=user_text)]},
            version="v1",
        ):
            etype = event.get("event")
            if etype == "on_chat_model_stream":
                data = event.get("data", {})
                chunk = data.get("chunk")
                # chunk may be an AIMessageChunk or similar; try to extract text
                if chunk is not None:
                    content = getattr(chunk, "content", None)
                    if isinstance(content, str) and content:
                        yield content
                    elif isinstance(content, list):
                        # When content is a list of parts
                        parts = []
                        for p in content:
                            text = getattr(p, "text", None)
                            if text:
                                parts.append(text)
                        if parts:
                            yield "".join(parts)
        if not tool_invoked:
            logger.warning(f"MCP tool '{rag_tool_name}' was NOT invoked for user text: {user_text!r}")

    return agent, astream_answer