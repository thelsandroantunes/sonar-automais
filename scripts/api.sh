#!/usr/bin/env bash
# Sobe a API em modo demonstração (dados fictícios, sem banco). Windows: rodar no Git Bash.
# http://localhost:8000/docs  ·  protótipo: http://localhost:8000/demo/
# ATENÇÃO: o servidor fica rodando neste terminal até Ctrl+C. Use outro terminal para git e testes.
set -e
cd "$(dirname "$0")/../backend"
if [ ! -d .venv ]; then python -m venv .venv; fi
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -q -r requirements.txt
echo "API em http://localhost:8000/docs — protótipo em http://localhost:8000/demo/ — Ctrl+C para parar"
uvicorn api.main:app --reload --port 8000
