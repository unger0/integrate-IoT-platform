#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo '[ERRO] Instale Docker Engine e docker-compose (consulte docs/05-arch-linux.md).' >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo '[ERRO] Docker Engine indisponível para este usuário.' >&2
  echo 'Verifique sudo systemctl enable --now docker.service e as permissões.' >&2
  exit 1
fi
printf 'Iniciando contêineres em %s\n' "$ROOT"
docker compose -f infra/compose.lab.yml up --build -d
echo 'Estado dos serviços:'
docker compose -f infra/compose.lab.yml ps
echo 'API: http://localhost:8000/docs'
echo 'Borda: http://localhost:8001/health'
echo 'Execute depois: ./scripts/linux/02-demonstrar-fluxo.sh'
