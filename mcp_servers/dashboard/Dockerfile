FROM evieai-mcp-base:local
# dashboard has no extra deps beyond base (fastapi, uvicorn, pydantic, httpx)
COPY app/ app/
EXPOSE 8009
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009"]
