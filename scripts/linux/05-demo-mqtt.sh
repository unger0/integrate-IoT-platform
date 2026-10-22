#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
if ! command -v python >/dev/null 2>&1; then echo '[ERRO] Python não instalado.' >&2; exit 1; fi
if ! docker info >/dev/null 2>&1; then echo '[ERRO] Docker Engine indisponível.' >&2; exit 1; fi
# venv impede instalar dependências no Python gerenciado pelo pacman.
if [[ ! -x .venv/bin/python ]]; then python -m venv .venv; fi
.venv/bin/python -m pip install 'paho-mqtt>=2,<3'
docker compose -f infra/compose.lab.yml --profile mqtt up --build -d
python scripts/aguardar_servicos.py --timeout 75
python scripts/demo_central.py  # garante dispositivo urbano cadastrado
.venv/bin/python scripts/demo_mqtt.py
echo 'Consulte o histórico em http://localhost:8000/api/v1/dispositivos/ar-centro-03/telemetria'
echo 'Logs: docker compose -f infra/compose.lab.yml logs --tail 50 mqtt-bridge'
