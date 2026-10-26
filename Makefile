up:    ; docker compose up --build -d && echo "Open http://localhost:8080"
down:  ; docker compose down
reset: ; docker compose down -v
logs:  ; docker compose logs -f
test:  ; cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements-dev.txt && pytest -q
