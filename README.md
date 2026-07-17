# nst_playground_er_diagram

ER diagram editor (`drawdb-clone`, React/Vite) plus a validator API
(`validator`, FastAPI + native Bliss engine) that checks a student's
diagram against a teacher's reference by graph isomorphism.

## Run with Docker

```sh
docker compose up -d --build
```

- Frontend: http://localhost:8080 — nginx serves the built app and proxies
  the API paths (`/health`, `/validate`, `/compare-names`, `/questions`)
  to the validator container, so no CORS setup is needed.
- The Bliss binary is compiled from source in the image build; nothing to
  install on the host.
- Question data lives in the `portal-data` named volume
  (`/data/portal.db` inside the validator container) and survives restarts.

### Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `CORS_ORIGINS` | validator env | `http://localhost:5173,http://127.0.0.1:5173` | comma-separated allowed origins (only needed for direct cross-origin API access) |
| `PORTAL_DB` | validator env | `/data/portal.db` (in Docker) | SQLite database path |
| `BLISS_BIN` | validator env | baked into image | path to the bliss binary |
| `VITE_VALIDATOR_URL` | frontend build arg | `''` (same-origin) | API base URL baked into the frontend bundle |

## Local development (without Docker)

```sh
# backend
cd validator && ./setup.sh          # one-time: builds vendor/bliss
pip install -r requirements.txt
uvicorn er_validator.api:app --port 8000

# frontend
cd drawdb-clone && npm install && npm run dev   # http://localhost:5173
```
