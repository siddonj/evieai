FROM evieai-mcp-base:local
# onedrive needs msal for Microsoft Graph auth
RUN uv pip install "msal==1.31.0"
# Build context is repo root, so COPY paths are relative to .
COPY mcp_servers/onedrive/app /app/app
COPY mcp_servers/common /app/mcp_servers/common
COPY mcp_servers/__init__.py /app/mcp_servers/__init__.py
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
