#!/usr/bin/env bash
# Smoke-test sem modificar os cadastros; requer Docker com API ativa.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python scripts/verificar_painel_v030.py
# Também testa endpoints listagem isoladamente, dentro do contêiner Python.
docker compose -f infra/compose.lab.yml exec -T api python -m unittest discover -s tests -v
