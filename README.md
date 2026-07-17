# nst_playground_er_diagram

ER diagram editor (`drawdb-clone`, React/Vite) plus a validator API
(`validator`, FastAPI + native Bliss engine) that checks a student's
diagram against a teacher's reference by graph isomorphism.

## Hosted version

- **Frontend:** https://kanishkranjan.github.io/fr/ — auto-deployed to GitHub
  Pages on every push to `main` (`.github/workflows/deploy-pages.yml`).
- **Backend:** one-click deploy of the validator API to Render's free tier
  (uses `render.yaml`):

  [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/KanishkRanjan/fr)

  After deploying, if Render assigns a URL other than
  `https://er-validator-fr.onrender.com`, update the `VALIDATOR_URL`
  repository variable (Settings → Secrets and variables → Actions →
  Variables) and re-run the Pages workflow so the frontend points at it.
  Free-tier notes: the service sleeps after ~15 min idle (first request
  takes ~1 min to wake) and has no persistent disk, so saved questions
  reset on redeploys.

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
