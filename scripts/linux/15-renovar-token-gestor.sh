#!/usr/bin/env bash
# Renova SOMENTE o JWT demonstrativo de gestor, sem reiniciar API ou borda.
# Não imprime o segredo ou token. Não usar em produção.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
command -v python >/dev/null || { echo '[ERRO] Python necessário.' >&2; exit 1; }
if [[ ! -f .env.protegido ]]; then
  echo '[ERRO] .env.protegido ausente; execute scripts/linux/09-iniciar-protegido.sh uma vez.' >&2
  exit 1
fi
if ! curl -fsS --max-time 5 http://127.0.0.1:8000/health | python -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("modo_protegido_demo") else 1)'; then
  echo '[ERRO] A API não está acessível no modo JWT. Verifique os serviços.' >&2
  exit 1
fi
umask 077
SECRET="$(sed -n 's/^IOT_LAB_JWT_SECRET=//p' .env.protegido | head -n 1)"
if [[ ${#SECRET} -lt 32 ]]; then
  echo '[ERRO] Chave JWT didática ausente ou inválida.' >&2; exit 1
fi
export IOT_LAB_JWT_SECRET="$SECRET"
mkdir -p runtime
chmod 700 runtime
TMP="$(mktemp runtime/.token-gestor.XXXXXX)"
trap 'rm -f "$TMP"' EXIT
python scripts/gerar_token_lab.py --inquilino coop-cerrado --papel gestor --sujeito gestor-laboratorio --segundos 3600 > "$TMP"
chmod 600 "$TMP"
mv -f "$TMP" runtime/token-gestor.txt
printf '[OK] Token local de gestor renovado por 1 hora, sem reiniciar contêineres.\n'
printf 'Arquivo privado: runtime/token-gestor.txt\n'
printf 'Confirme: ./scripts/linux/14-verificar-acesso-painel.sh\n'
printf 'Cole o token apenas no formulário do painel local e pressione "Validar e entrar".\n'
