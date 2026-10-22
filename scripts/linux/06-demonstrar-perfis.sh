#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python scripts/aguardar_servicos.py --timeout 75
# Testa regras isoladamente dentro da imagem com dependências do backend.
docker compose -f infra/compose.lab.yml exec -T api python -m unittest discover -s tests -v
# A primeira demonstração cadastrou o sensor no PostgreSQL.
python scripts/demo_perfis.py
