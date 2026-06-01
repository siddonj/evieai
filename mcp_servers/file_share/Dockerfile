FROM evieai-mcp-base:local
# file_share has no extra deps beyond base (fastapi, uvicorn, pydantic, httpx)
# Build context is repo root, so COPY paths are relative to .
COPY mcp_servers/file_share/app /app/app
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
