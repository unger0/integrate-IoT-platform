#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
docker compose -f infra/compose.lab.yml up --build -d --force-recreate api edge
printf '[OK] API e borda retornaram ao laboratório simples. Os volumes foram preservados.\n'
printf 'Não exponha este laboratório na internet.\n'
