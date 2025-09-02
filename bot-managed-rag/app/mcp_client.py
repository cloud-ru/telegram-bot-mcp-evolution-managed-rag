from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import Any, Iterable

from mcp import ClientSession
from mcp.client.sse import sse_client


class McpClient:
    """Async MCP client for SSE transport.

    Connects to a remote MCP server by URL and provides tool calling helpers.
    """

    def __init__(self, url: str, transport: str = "sse") -> None:
        self._url = url
        self._transport = (transport or "sse").lower()
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "McpClient":
        if self._transport != "sse":
            raise NotImplementedError(
                f"Transport '{self._transport}' is not implemented in this client yet. Use 'sse'."
            )
        stack = AsyncExitStack()
        # Open SSE streams within the same exit stack
        read_stream, write_stream = await stack.enter_async_context(sse_client(url=self._url))
        # Open MCP session tied to the same stack
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()
        self._stack = stack
        self._session = session
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._stack is None:
            return
        try:
            await self._stack.aclose()
        except (asyncio.CancelledError, GeneratorExit):
            return
        except RuntimeError as e:
            if "exit cancel scope in a different task" in str(e).lower():
                return
            raise
        finally:
            self._stack = None
            self._session = None

    @property
    def session(self) -> ClientSession:
        assert self._session is not None, "MCP session is not initialized"
        return self._session

    async def list_tools(self) -> list[str]:
        resp = await self.session.list_tools()
        return [t.name for t in resp.tools]

    async def call_tool_text(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool and return concatenated text content.

        This assumes the server returns a list of content blocks where text blocks
        are of type 'text' with field 'text'. Non-text results are ignored.
        """
        result = await self.session.call_tool(name=name, arguments=arguments)
        # result.content could be a list of content blocks
        blocks: Iterable[Any] = getattr(result, "content", [])
        texts: list[str] = []
        for b in blocks:
            text = getattr(b, "text", None)
            if text:
                texts.append(text)
        return "\n".join(texts).strip()