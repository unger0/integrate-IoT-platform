#!/usr/bin/env bash
# Backup + reconstrução segura, preserva modo aberto ou JWT demonstrativo.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null || { echo '[ERRO] Docker não encontrado.' >&2; exit 1; }
command -v curl >/dev/null || { echo '[ERRO] curl não encontrado.' >&2; exit 1; }
MODE="$(docker compose -f infra/compose.lab.yml exec -T api sh -c 'printf "%s" "${IOT_LAB_AUTH_MODE:-off}"' 2>/dev/null)" || {
  echo '[ERRO] API atual não está em execução; confira docker compose -f infra/compose.lab.yml ps' >&2; exit 1;
}
[[ "$MODE" == 'jwt' || "$MODE" == 'off' ]] || { echo "[ERRO] Modo inesperado: $MODE" >&2; exit 1; }
umask 077
mkdir -p backups
BACKUP="backups/iot-pre-v070-$(date +%Y%m%d-%H%M%S).sql"
echo '[1/4] Backup do PostgreSQL...'
if ! docker compose -f infra/compose.lab.yml exec -T db pg_dump -U iot_lab -d iot_laboratorio > "$BACKUP"; then
  rm -f "$BACKUP"; echo '[ERRO] Backup falhou. Atualização cancelada.' >&2; exit 1
fi
if [[ ! -s "$BACKUP" ]] || ! grep -q 'PostgreSQL database dump' "$BACKUP"; then
  rm -f "$BACKUP"; echo '[ERRO] Backup inválido. Atualização cancelada.' >&2; exit 1
fi
printf '[OK] Backup: %s\n' "$BACKUP"
echo '[2/4] Reconstrução e reinício dos serviços...'
if [[ "$MODE" == 'jwt' ]]; then
  ./scripts/linux/09-iniciar-protegido.sh
  echo '[AVISO] O token do gestor foi renovado. Use o arquivo local runtime/token-gestor.txt no painel.'
else
  ./scripts/linux/01-iniciar-laboratorio.sh
fi
for _ in $(seq 1 30); do
  if curl --fail --silent --max-time 2 http://127.0.0.1:8000/health >/dev/null; then break; fi
  sleep 1
done
echo '[3/4] Conferindo versão e execução de testes...'
if ! curl -fsS --max-time 5 http://127.0.0.1:8000/openapi.json | python -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)["info"]["version"]=="0.7.0" else 1)'; then
  echo '[ERRO] A API não apresentou a versão 0.7.0; confira os logs e o build.' >&2; exit 1
fi
docker compose -f infra/compose.lab.yml exec -T api env IOT_LAB_AUTH_MODE=off \
  python -m unittest discover -s tests -q
echo '[4/4] Verificação somente-leitura...'
./scripts/linux/18-validar-observabilidade.sh
echo '[OK] v0.7.0 atualizada e verificada (laboratório, não homologação).'
