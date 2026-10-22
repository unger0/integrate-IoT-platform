"""Smoke-test somente leitura: verificações 401, 403, 200 no modo jwt demo.
Não registra nem altera dispositivos. Exige scripts/linux/09-iniciar-protegido.sh.
"""
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
TOKEN=(ROOT/'runtime/token-gestor.txt').read_text().strip()
BASE='http://127.0.0.1:8000'


def request(path, token=None):
    headers={'Authorization': 'Bearer '+token} if token else {}
    try:
        with urlopen(Request(BASE+path,headers=headers),timeout=8) as resp:
            return resp.status, json.load(resp)
    except HTTPError as e:
        return e.code, json.load(e)

health=request('/health')[1]
assert health['modo_protegido_demo'] is True, 'Modo protegido não está ativado'
assert request('/api/v1/dispositivos?inquilino=coop-cerrado')[0] == 401
ok,ident=request('/api/v1/identidade',TOKEN)
assert ok==200 and ident['inquilino']=='coop-cerrado' and ident['papel']=='gestor'
assert request('/api/v1/dispositivos?inquilino=outra-organizacao',TOKEN)[0] == 403
assert request('/api/v1/dispositivos?inquilino=coop-cerrado',TOKEN)[0] == 200
print('[OK] 401 sem token; 403 acesso cruzado; 200 token válido para organização autorizada')
print('[OK] Smoke-test sem gravação de dados. NÃO é certificação de segurança ou OIDC.')
