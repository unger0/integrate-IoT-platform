#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
docker compose -f infra/compose.lab.yml exec -T api env IOT_LAB_AUTH_MODE=off python -m unittest discover -s tests -v
python scripts/verificar_modo_protegido.py
