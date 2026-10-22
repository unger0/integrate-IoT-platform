#!/usr/bin/env bash
# Laboratório local; inicia a interface React. Mantém o terminal ocupado até Ctrl+C.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
if ! command -v npm >/dev/null 2>&1; then
  echo '[ERRO] npm não encontrado. Instale nodejs e npm com pacman.' >&2
  exit 1
fi
if ! curl --fail --silent --max-time 4 http://127.0.0.1:8000/health >/dev/null; then
  echo '[ERRO] API não responde. Execute ./scripts/linux/01-iniciar-laboratorio.sh' >&2
  exit 1
fi
cd apps/web
if [[ ! -d node_modules ]]; then
  echo 'Instalando dependências React/Vite (necessita acesso à internet na primeira vez)...'
  npm install --no-audit --no-fund
fi
printf '\nPainel: http://127.0.0.1:5173\nPressione Ctrl+C para encerrar o frontend.\n\n'
npm run dev
