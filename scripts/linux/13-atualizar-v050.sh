#!/usr/bin/env bash
# Backup, rebuild e validação rápida do laboratório v0.5 (sem apagar volumes).
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null || { echo '[ERRO] Docker não encontrado' >&2; exit 1; }
command -v curl >/dev/null || { echo '[ERRO] curl não encontrado' >&2; exit 1; }
# Falhar explicitamente se não for possível detectar o modo corrente.
MODE="$(docker compose -f infra/compose.lab.yml exec -T api sh -c 'printf "%s" "${IOT_LAB_AUTH_MODE:-off}"' 2>/dev/null)" || {
  echo '[ERRO] API anterior não está em execução. Inicie com script 01 (aberto) ou 09 (protegido) e repita.' >&2
  exit 1
}
if [[ "$MODE" != "off" && "$MODE" != "jwt" ]]; then
  echo "[ERRO] Modo inesperado: $MODE" >&2; exit 1
fi
umask 077
mkdir -p backups
BACKUP="backups/iot-pre-v050-$(date +%Y%m%d-%H%M%S).sql"
echo 'Salvando backup PostgreSQL...'
if ! docker compose -f infra/compose.lab.yml exec -T db \
     pg_dump -U iot_lab -d iot_laboratorio > "$BACKUP"; then
  rm -f "$BACKUP"
  echo '[ERRO] Backup falhou; atualização cancelada.' >&2; exit 1
fi
if [[ ! -s "$BACKUP" ]] || ! grep -q 'PostgreSQL database dump' "$BACKUP"; then
  rm -f "$BACKUP"
  echo '[ERRO] Backup vazio ou sem cabeçalho; atualização cancelada.' >&2; exit 1
fi
echo "[OK] Backup gerado: $BACKUP"
if [[ "$MODE" == 'jwt' ]]; then
  echo 'Reconstruindo no modo JWT DEMONSTRATIVO...'
  ./scripts/linux/09-iniciar-protegido.sh
  echo '[ATENÇÃO] Token temporário foi renovado. Copie novamente runtime/token-gestor.txt no painel.'
else
  echo 'Reconstruindo em modo aberto de laboratório...'
  ./scripts/linux/01-iniciar-laboratorio.sh
fi
for _ in $(seq 1 25); do
  if curl --fail --silent --max-time 3 http://127.0.0.1:8000/health >/dev/null; then break; fi
  sleep 1
done
curl --fail --silent --max-time 3 http://127.0.0.1:8000/health >/dev/null || {
  echo '[ERRO] API não respondeu; confira docker compose ... logs api' >&2; exit 1;
}
OPENAPI="$(curl --fail --silent --max-time 5 http://127.0.0.1:8000/openapi.json)" || {
  echo '[ERRO] OpenAPI não pôde ser consultado.' >&2; exit 1
}
if [[ "$OPENAPI" != *'"version":"0.5.0"'* ]]; then
  echo '[ERRO] Versão 0.5.0 não encontrada no documento OpenAPI.' >&2; exit 1
fi
echo '[OK] API v0.5.0 respondendo. Executando testes unitários...'
docker compose -f infra/compose.lab.yml exec -T api env IOT_LAB_AUTH_MODE=off \
  python -m unittest discover -s tests -q
printf '\n[OK] Atualização inicial validada. Próximo: ./scripts/linux/12-demonstrar-alarmes.sh\n'
