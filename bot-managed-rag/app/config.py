from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


def _getenv(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    mcp_server_url: str
    mcp_rag_tool_name: str
    mcp_transport: str

    gigachat_credentials: str | None
    gigachat_scope: str
    gigachat_model: str
    gigachat_temperature: float
    gigachat_verify_ssl: bool

    stream_edit_interval_sec: float
    stream_min_chars_delta: int

    @staticmethod
    def load() -> "Settings":
        # Telegram
        telegram_token = _getenv("TELEGRAM_BOT_TOKEN", required=True)  # type: ignore[arg-type]

        # MCP
        mcp_server_url = _getenv("MCP_SERVER_URL", required=True)  # type: ignore[arg-type]
        mcp_rag_tool_name = _getenv("MCP_RAG_TOOL_NAME", "rag_query")  # type: ignore[assignment]
        mcp_transport = (_getenv("MCP_TRANSPORT", "sse") or "sse").lower()  # sse|streamable-http (future)

        # GigaChat
        gigachat_credentials = _getenv("GIGACHAT_CREDENTIALS")
        gigachat_scope = _getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
        gigachat_model = _getenv("GIGACHAT_MODEL", "GigaChat")
        gigachat_temperature = float(_getenv("GIGACHAT_TEMPERATURE", "0.7"))
        gigachat_verify_ssl = _getenv("GIGACHAT_VERIFY_SSL", "false")

        if not gigachat_credentials:
            raise RuntimeError(
                "Missing GigaChat auth: set either GIGACHAT_CREDENTIALS (client_id:client_secret)."
            )

        # Streaming config
        stream_edit_interval_sec = float(_getenv("STREAM_EDIT_INTERVAL_SEC", "0.4") or 0.4)
        stream_min_chars_delta = int(_getenv("STREAM_MIN_CHARS_DELTA", "48") or 48)

        return Settings(
            telegram_token=telegram_token,
            mcp_server_url=mcp_server_url,
            mcp_rag_tool_name=mcp_rag_tool_name,
            mcp_transport=mcp_transport,
            gigachat_credentials=gigachat_credentials,
            gigachat_scope=gigachat_scope,
            gigachat_model=gigachat_model,
            gigachat_temperature=gigachat_temperature,
            gigachat_verify_ssl=gigachat_verify_ssl,
            stream_edit_interval_sec=stream_edit_interval_sec,
            stream_min_chars_delta=stream_min_chars_delta,
        )