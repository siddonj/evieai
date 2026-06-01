FROM evieai-mcp-base:local
# sql needs newer versions of uvicorn, httpx, pydantic
RUN uv pip install "uvicorn[standard]==0.34.2" "httpx==0.28.1" "pydantic==2.11.4"
COPY app/ app/
EXPOSE 8004
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
