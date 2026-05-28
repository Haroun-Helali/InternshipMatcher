#!/usr/bin/env bash
# Launch the Internship RAG app on macOS / Linux.
# Mirrors start.ps1. Usage: ./start.sh [install|backend|frontend|all]

set -euo pipefail

TASK="${1:-all}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

c_section() { printf '\n\033[36m=== %s ===\033[0m\n' "$1"; }
c_info()    { printf '\033[90m%s\033[0m\n' "$1"; }
c_ok()      { printf '\033[32m%s\033[0m\n' "$1"; }
c_warn()    { printf '\033[33m%s\033[0m\n' "$1" >&2; }

pick_python() {
  for cmd in python3.11 python3.12 python3.10 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      local v
      v="$("$cmd" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "")"
      case "$v" in
        3.10|3.11|3.12|3.13) echo "$cmd"; return 0 ;;
      esac
    fi
  done
  c_warn "Python 3.10+ not found. Install via 'brew install python@3.11' or your package manager."
  return 1
}

ensure_venv() {
  if [ ! -d "venv" ]; then
    c_section "Create Python venv"
    PY="$(pick_python)"
    "$PY" -m venv venv
  else
    c_info "venv already exists"
  fi
  # shellcheck disable=SC1091
  . ./venv/bin/activate
  c_ok "Python: $(python --version)"
}

install_backend_deps() {
  c_section "Install backend Python deps"
  python -m pip install --upgrade pip
  pip install -r requirements.txt
}

ollama_up() { curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; }

ensure_ollama() {
  c_section "Ensure Ollama running"
  if ! command -v ollama >/dev/null 2>&1; then
    c_warn "ollama binary not found. Install via 'brew install ollama' (macOS) or see https://ollama.ai/download."
    return 0
  fi
  if ! ollama_up; then
    c_info "Starting 'ollama serve' in background..."
    nohup ollama serve >/tmp/ollama.log 2>&1 &
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      ollama_up && break
      sleep 0.5
    done
  fi
  if ollama_up; then
    c_ok "Ollama reachable at http://localhost:11434"
  else
    c_warn "Ollama is not reachable; LLM calls will fail."
  fi
}

ensure_ollama_models() {
  command -v ollama >/dev/null 2>&1 || return 0
  ollama_up || return 0
  for model in llama3.2:latest mxbai-embed-large:latest; do
    if ! ollama list | awk 'NR>1{print $1}' | grep -qx "$model"; then
      c_info "Pulling $model (this may take several minutes)..."
      ollama pull "$model"
    else
      c_info "$model already pulled"
    fi
  done
}

install_frontend_deps() {
  c_section "Install frontend Node deps"
  if ! command -v npm >/dev/null 2>&1; then
    c_warn "npm not found. Install Node.js 18+ from https://nodejs.org."
    return 0
  fi
  (
    cd frontend
    if [ ! -d node_modules ]; then npm install; else c_info "node_modules present"; fi
  )
}

ensure_runtime_dirs() {
  mkdir -p uploads temp_files logs chroma_data
}

ensure_env() {
  if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    c_info "Created .env from .env.example"
  fi
}

start_backend() {
  c_section "Start backend"
  ensure_runtime_dirs
  ensure_env
  nohup ./venv/bin/python -m backend.app.main >logs/backend.log 2>&1 &
  echo $! >.backend.pid
  c_ok "Backend starting on http://localhost:8000 (pid $(cat .backend.pid), logs/backend.log)"
}

start_frontend() {
  c_section "Start frontend"
  command -v npm >/dev/null 2>&1 || { c_warn "npm not found, skipping frontend"; return 0; }
  (
    cd frontend
    [ -d node_modules ] || npm install
    nohup npm run dev >../logs/frontend.log 2>&1 &
    echo $! >../.frontend.pid
  )
  c_ok "Frontend starting on http://localhost:3000 (pid $(cat .frontend.pid), logs/frontend.log)"
}

case "$TASK" in
  install)
    ensure_venv
    install_backend_deps
    ensure_ollama
    ensure_ollama_models
    install_frontend_deps
    c_ok "Install complete"
    ;;
  backend)
    ensure_venv
    ensure_ollama
    start_backend
    ;;
  frontend)
    install_frontend_deps
    start_frontend
    ;;
  all)
    ensure_venv
    install_backend_deps
    ensure_ollama
    ensure_ollama_models
    install_frontend_deps
    start_backend
    start_frontend
    c_ok "All services starting. Tail logs/backend.log and logs/frontend.log to follow output."
    ;;
  *)
    c_warn "Unknown task: $TASK"
    echo "Usage: $0 [install|backend|frontend|all]" >&2
    exit 1
    ;;
esac
