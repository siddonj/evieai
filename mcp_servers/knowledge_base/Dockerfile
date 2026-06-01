ARG BASE_IMAGE=evieai-mcp-base:local
FROM ${BASE_IMAGE}
# knowledge_base has no extra deps beyond base (fastapi, uvicorn, pydantic, httpx)
COPY app/ app/
EXPOSE 8005
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
