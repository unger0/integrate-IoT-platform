#!/usr/bin/env bash
# INICIA MODO PROTEGIDO DIDÁTICO - NUNCA PRODUÇÃO.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
command -v python >/dev/null || { echo 'Python necessário' >&2; exit 1; }
command -v docker >/dev/null || { echo 'Docker necessário' >&2; exit 1; }
mkdir -p runtime
chmod 700 runtime
umask 077
if [[ ! -f .env.protegido ]]; then
  SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  printf 'IOT_LAB_JWT_SECRET=%s\n' "$SECRET" > .env.protegido
fi
# Ler apenas a própria variável gerada pelo script; sem executar conteúdo arbitrário.
SECRET="$(sed -n 's/^IOT_LAB_JWT_SECRET=//p' .env.protegido | head -n 1)"
if [[ ${#SECRET} -lt 32 ]]; then
  echo '[ERRO] Chave inválida em .env.protegido' >&2; exit 1
fi
export IOT_LAB_JWT_SECRET="$SECRET"
# Em toda inicialização, renovar tokens temporários de borda, ponte MQTT e usuário.
EDGE="$(python scripts/gerar_token_lab.py --inquilino coop-cerrado --papel borda --sujeito borda-local --segundos 28800)"
MQTT="$(python scripts/gerar_token_lab.py --inquilino coop-cerrado --papel integrador --sujeito ponte-mqtt-local --segundos 28800)"
python scripts/gerar_token_lab.py --inquilino coop-cerrado --papel gestor --sujeito gestor-laboratorio --segundos 3600 > runtime/token-gestor.txt
chmod 600 .env.protegido runtime/token-gestor.txt
export IOT_LAB_EDGE_BEARER="$EDGE"
export IOT_LAB_MQTT_BEARER="$MQTT"

docker compose -f infra/compose.lab.yml -f infra/compose.auth-demo.yml up --build -d --force-recreate api edge
printf '\n[OK] Modo protegido DIDÁTICO habilitado para API e borda.\n'
printf 'Token temporário de gestor: %s/runtime/token-gestor.txt\n' "$ROOT"
printf 'Abra o painel, copie o token e clique "Usar token".\n'
printf 'Não use os scripts antigos de ingestão sem tokens nesse modo.\n'
printf 'Para voltar ao laboratório simples: ./scripts/linux/11-restaurar-laboratorio.sh\n'
