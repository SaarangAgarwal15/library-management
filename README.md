# Marginalia — Containerized Library Management System

FastAPI + PostgreSQL + Nginx, orchestrated with Docker Compose, tested and shipped by GitHub Actions.

```
Browser ──► nginx :8080 ──/api──► FastAPI :8000 ──► PostgreSQL (volume)
```

## Run on your Mac

1. Install tools (Terminal):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"   # skip if you have brew
   brew install --cask docker && brew install git
   open -a Docker      # accept prompts, wait until the whale icon says "running"
   ```
2. Start the app from this folder:
   ```bash
   make up             # or: docker compose up --build -d
   ```
3. Open http://localhost:8080 (health check: http://localhost:8080/api/health).

Other commands: `make logs`, `make down` (keep data), `make reset` (wipe data), `make test`.

## DevOps pieces
| Area | Where |
|---|---|
| Containers (non-root user, healthchecks) | `backend/Dockerfile`, `frontend/Dockerfile` |
| Orchestration (health-gated startup, volume, restart policy) | `docker-compose.yml` |
| CI: lint (ruff) + unit tests | `.github/workflows/ci.yml` → `test` |
| CI: full-stack smoke test in Compose | `smoke` job |
| CD: build, Trivy vulnerability scan, push to GHCR (tagged by commit SHA + latest) | `publish` job |

## Turn on CI/CD
```bash
git init && git add . && git commit -m "Initial commit"
# create an empty repo on github.com, then:
git remote add origin https://github.com/<you>/library.git
git branch -M main && git push -u origin main
```
Open the repo's **Actions** tab. Pull requests run tests and the smoke test; pushes to `main` also publish images to `ghcr.io/<you>/library-backend` and `library-frontend`.

## Troubleshooting
- `Cannot connect to the Docker daemon`: Docker Desktop isn't running yet; open it and retry.
- Port 8080 busy: change `"8080:80"` in `docker-compose.yml`.
- Fresh start: `make reset && make up`.
