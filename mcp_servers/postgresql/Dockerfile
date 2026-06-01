FROM evieai-mcp-base:local
# postgresql needs asyncpg and newer versions of uvicorn, pydantic
RUN uv pip install "uvicorn[standard]==0.34.2" "pydantic==2.11.4" "asyncpg==0.29.0"
COPY app/ app/
EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
