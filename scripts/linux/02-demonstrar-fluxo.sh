#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
command -v python >/dev/null 2>&1 || { echo '[ERRO] Python não encontrado.' >&2; exit 1; }
echo 'Aguardando API central e nó de borda...'
python scripts/aguardar_servicos.py --timeout 75
echo '== Cadastro e telemetria urbana =='
python scripts/demo_central.py
echo '== Envio de telemetria rural à borda =='
python scripts/demo_borda.py
echo '== Verificação de persistência e sincronização =='
python scripts/verificar_fluxo.py --timeout 60
echo 'Consulte o painel com Node/npm opcional: cd apps/web && npm install && npm run dev'
