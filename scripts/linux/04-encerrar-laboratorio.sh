#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
if ! command -v docker >/dev/null 2>&1; then echo '[ERRO] Docker não encontrado.' >&2; exit 1; fi
docker compose -f infra/compose.lab.yml --profile mqtt down
echo 'Laboratório encerrado. Volumes de dados preservados (não usamos -v).'
