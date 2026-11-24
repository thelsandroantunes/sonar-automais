#!/usr/bin/env bash
# Opcional: PostgreSQL local (Docker) + migrações + dados fictícios no banco.
set -e
cd "$(dirname "$0")/.."
docker compose up -d
cd backend
if [ ! -d .venv ]; then python -m venv .venv; fi
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -q -r requirements.txt
python -m coleta.migrar
python -m coleta.semear
