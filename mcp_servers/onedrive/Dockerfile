FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY mcp_servers/onedrive/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mcp_servers/onedrive/app /app/app
COPY mcp_servers/common /app/mcp_servers/common
COPY mcp_servers/__init__.py /app/mcp_servers/__init__.py

EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
