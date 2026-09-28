# Local development without Docker.
#
#   make run   — rebuild the frontend, then serve API + built SPA on one port
#   make dev   — hot-reload development: uvicorn (background) + vite dev server
#
# System deps (macOS): brew install espeak-ng ffmpeg
# First run creates backend/.venv and installs backend + frontend deps.

PORT ?= 8900

BACKEND := backend
FRONTEND := frontend
PY := $(BACKEND)/.venv/bin/python
BACKEND_STAMP := $(BACKEND)/.venv/.requirements.stamp

.DEFAULT_GOAL := run
.PHONY: run dev backend frontend build test setup clean help

help:
	@echo "make run      build the frontend, then serve everything at http://localhost:$(PORT)"
	@echo "make dev      hot-reload dev: API on :$(PORT) + vite dev server on :5173"
	@echo "make backend  run the API alone"
	@echo "make frontend run the vite dev server alone (expects the API on :$(PORT))"
	@echo "make build    build the frontend into $(FRONTEND)/dist"
	@echo "make test     backend pytest + frontend typecheck/lint"
	@echo "make setup    create the venv and install backend + frontend deps"
	@echo "make clean    remove build artifacts (dist, caches)"

run: backend-deps build
	cd $(BACKEND) && .venv/bin/python -m uvicorn app.main:app --port $(PORT)

# backend in the background (auto-reload), vite dev server in the foreground;
# stopping vite (Ctrl-C) also stops the API. uvicorn runs with --app-dir so
# the background pid is uvicorn itself, not a wrapper shell.
dev: backend-deps frontend-deps
	$(PY) -m uvicorn app.main:app --app-dir $(BACKEND) --port $(PORT) --reload & \
	pid=$$!; \
	cleanup() { kill $$pid 2>/dev/null; pkill -P $$pid 2>/dev/null; }; \
	trap cleanup EXIT INT TERM; \
	cd $(FRONTEND) && npm run dev; \
	status=$$?; \
	cleanup; \
	exit $$status

backend: backend-deps
	cd $(BACKEND) && .venv/bin/python -m uvicorn app.main:app --port $(PORT) --reload

frontend: frontend-deps
	cd $(FRONTEND) && npm run dev

build: frontend-deps
	cd $(FRONTEND) && npm run build

test: backend-deps frontend-deps
	cd $(BACKEND) && .venv/bin/python -m pytest tests/ -q
	cd $(FRONTEND) && npm run lint && npm run build

setup: backend-deps frontend-deps

backend-deps: $(BACKEND_STAMP)

$(BACKEND_STAMP): $(BACKEND)/requirements.txt
	cd $(BACKEND) && (test -x .venv/bin/python || python3.13 -m venv .venv)
	$(BACKEND)/.venv/bin/pip install -q -r $(BACKEND)/requirements.txt
	touch $@

frontend-deps:
	cd $(FRONTEND) && (test -d node_modules || npm install)

clean:
	rm -rf $(FRONTEND)/dist $(BACKEND)/.pytest_cache
