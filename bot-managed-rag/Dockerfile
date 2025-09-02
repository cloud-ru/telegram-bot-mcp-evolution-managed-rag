# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Install uv for fast, reproducible Python dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy source code
COPY . .

RUN uv sync

# Run the bot
CMD ["uv", "run", "python", "main.py"]