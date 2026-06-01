ARG BASE_IMAGE=evieai-mcp-base:local
FROM ${BASE_IMAGE}
# memory has no extra deps beyond base (fastapi, uvicorn, pydantic, httpx)
COPY app/ app/
EXPOSE 8004
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
