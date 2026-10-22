#!/usr/bin/env bash
# Diagnóstico SOMENTE-LEITURA do acesso à interface. Nunca exibe o token JWT.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
command -v python >/dev/null || { echo '[ERRO] Python necessário.' >&2; exit 1; }
python - <<'PY'
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import sys

ROOT=Path.cwd()
BASE='http://127.0.0.1:8000'

def call(path, token=None):
    headers={}
    if token:
        headers['Authorization']='Bearer '+token
    try:
        with urlopen(Request(BASE+path, headers=headers),timeout=5) as response:
            return response.status,json.load(response)
    except HTTPError as e:
        try: data=json.load(e)
        except (ValueError, OSError): data={}
        return e.code,data

try:
    status,health=call('/health')
except (URLError,TimeoutError,OSError) as exc:
    print('[ERRO] API não acessível em http://127.0.0.1:8000/health')
    print('Confira: docker compose -f infra/compose.lab.yml ps')
    sys.exit(1)
if status!=200 or health.get('status')!='ok':
    print('[ERRO] /health respondeu inesperadamente:', status)
    sys.exit(1)
print('[OK] API central acessível pela rede local do notebook.')
if not health.get('modo_protegido_demo'):
    print('[AVISO] Modo aberto de laboratório; não é autenticação de produção.')
    sys.exit(0)
print('[OK] Modo JWT didático ativo.')
path=ROOT/'runtime/token-gestor.txt'
if not path.is_file():
    print('[ERRO] Token local ausente. Execute ./scripts/linux/15-renovar-token-gestor.sh')
    sys.exit(2)
token=path.read_text().strip()
try:
    code,identity=call('/api/v1/identidade',token)
except (URLError,TimeoutError,OSError):
    print('[ERRO] Falha de rede ao consultar /api/v1/identidade')
    sys.exit(1)
if code==401:
    print('[ERRO] Token inválido ou expirado. Execute ./scripts/linux/15-renovar-token-gestor.sh')
    sys.exit(2)
if code!=200 or not identity.get('autenticado'):
    print(f'[ERRO] Identidade não validada: HTTP {code}')
    sys.exit(2)
print('[OK] Token válido; organização:', identity.get('inquilino'), '| papel:', identity.get('papel'))
from urllib.parse import quote
organization=quote(identity['inquilino'],safe='')
try:
    code,data=call(f'/api/v1/dispositivos?inquilino={organization}&limite=5',token)
except (URLError,TimeoutError,OSError):
    print('[ERRO] Falha de rede ao consultar inventário.')
    sys.exit(1)
if code==200:
    print('[OK] Inventário autorizado. Dispositivos retornados na amostra:',len(data.get('dispositivos',[])))
    print('[OK] Copie o token apenas no navegador local; não cole em chats ou capturas de tela.')
else:
    print(f'[ERRO] Inventário recusado (HTTP {code}); confira o papel e a organização.')
    sys.exit(2)
PY
