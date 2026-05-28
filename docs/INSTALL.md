# EvieAI Install Guide

This guide covers local install (Docker) and production deployment (Azure via Terraform).

## 1) Local install (recommended)

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Git
- 8+ GB RAM allocated to Docker

### Steps

```bash
git clone https://github.com/siddonj/evieai.git
cd evieai
cp .env.example .env
cp web_ui/.env.example web_ui/.env
```

Edit `.env` with at least:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- (optional) `AZURE_OPENAI_DEPLOYMENT` (default `gpt-4o`)

Start everything:

```bash
docker compose up --build
```

Open:

- UI: `http://localhost:5173`
- API: `http://localhost:8000`

### Validate startup

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
```

---

## 2) Local dev without Docker (optional)

### Backend

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r orchestrator/requirements.txt
PYTHONPATH=. uvicorn orchestrator.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd web_ui
npm ci
npm run dev -- --host 0.0.0.0
```

---

## 3) Production install (Azure)

Use Terraform in `terraform/` as the source of truth.

```bash
cd terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

After apply, capture outputs:

- `orchestrator_url`
- `ui_default_hostname`
- `acr_login_server`
- `key_vault_name`

Then follow deployment details in `docs/DEPLOYMENT.md`.

---

## 4) Test commands

```bash
# backend unit tests
python -m venv .venv
source .venv/bin/activate
pip install -r tests/requirements.txt
pytest -q tests/unit

# frontend build
cd web_ui
npm ci
npm run build
```

---

## 5) Core local ports

- API: `8000`
- UI: `5173`
- DAB: `5000`
- MCPs: `8001`–`8009` (service-specific)
