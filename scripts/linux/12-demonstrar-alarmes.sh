#!/usr/bin/env bash
# Testes unitários + demonstração de alarmes; cria registros SINTÉTICOS.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
if ! curl --fail --silent --max-time 5 http://127.0.0.1:8000/health >/dev/null; then
  echo '[ERRO] API indisponível. Inicie com o script 01 ou 09.' >&2; exit 1
fi
docker compose -f infra/compose.lab.yml exec -T api env IOT_LAB_AUTH_MODE=off \
  python -m unittest discover -s tests -v
python scripts/demo_alarmes.py
