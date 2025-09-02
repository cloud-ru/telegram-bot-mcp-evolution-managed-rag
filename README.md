# Agentic RAG Telegram Bot + MCP Managed RAG

Двухсервисный проект:
- mcp-managed-rag — MCP-сервер (SSE), который ходит в Evolution Managed RAG и отдает агенту релевантный контекст по запросу пользователя.
- bot-managed-rag — Telegram-бот c LangGraph (ReAct-агент) и GigaChat, который вызывает удаленный MCP-инструмент и стримит ответ пользователю.

## Архитектура (вкратце)
1) Пользователь пишет боту в Telegram.
2) Агент (GigaChat + tool) вызывает инструмент `request_to_rag` на удаленном MCP-сервере по URL.
3) MCP-сервер обращается к Managed RAG, форматирует найденные документы в удобный контекст и возвращает его агенту.
4) Ответ LLM стримится в Telegram через редактирование сообщения.

## Требования
- Аккаунт/доступ к Evolution Managed RAG (ключи сервисного аккаунта)
- Токен Telegram-бота
- Доступ к GigaChat API

## Переменные окружения

bot-managed-rag:
- TELEGRAM_BOT_TOKEN — токен Telegram-бота
- MCP_SERVER_URL — URL SSE эндпоинта MCP (например, http://localhost:8003/sse)
- MCP_RAG_TOOL_NAME — имя инструмента на MCP-сервере. Укажите: `request_to_rag` 
- MCP_TRANSPORT — транспорт MCP, сейчас поддержан `sse`
- GIGACHAT_CREDENTIALS — ключ авторизации для GigaChat
- GIGACHAT_SCOPE - версия API
- GIGACHAT_MODEL - Название модели
- GIGACHAT_TEMPERATURE - температура ответа
- GIGACHAT_VERIFY_SSL — `true|false`
- STREAM_EDIT_INTERVAL_SEC — интервал редактирования сообщения
- STREAM_MIN_CHARS_DELTA — минимальный накопленный текст для редактирования

mcp-managed-rag:
- SERVICE_ACCOUNT_KEY_ID — ID ключа сервисного аккаунта (не обязательно)
- SERVICE_ACCOUNT_KEY_SECRET — секрет ключа сервисного аккаунта (не обязательно)
- EVOLUTION_PROJECT_ID — ID проекта
- KNOWLEDGE_BASE_ID — ID базы знаний
- KNOWLEDGE_BASE_VERSION_ID — ID версии базы знаний
- RETRIEVE_LIMIT — лимит возвращаемых документов

## Быстрый старт через Docker Compose
Запустите:
```
docker compose up --build
```
