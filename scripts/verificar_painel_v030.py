"""Smoke test read-only da interface backend v0.3.0. Apenas biblioteca padrão."""
import json
from urllib.parse import quote
from urllib.request import urlopen

HOST='http://127.0.0.1:8000'
TENANT='coop-cerrado'

def get(path):
    with urlopen(HOST + path,timeout=8) as resp:
        assert resp.status == 200, f'HTTP {resp.status}: {path}'
        return json.load(resp)

health=get('/health')
assert health['status']=='ok'
version=get('/openapi.json')['info']['version']
assert version=='0.3.0', f'API esperada 0.3.0; recebida {version}'
q=quote(TENANT,safe='')
domains=get(f'/api/v1/catalogo/dominios?inquilino={q}')
profiles=get(f'/api/v1/catalogo/perfis?inquilino={q}')
devices=get(f'/api/v1/dispositivos?inquilino={q}')
assert domains['inquilino']==profiles['inquilino']==devices['inquilino']==TENANT
assert isinstance(domains['dominios'], list) and isinstance(profiles['perfis'], list)
assert isinstance(devices['dispositivos'], list)
print('[OK] API central 0.3.0 funcionando')
print(f"[OK] Domínios: {len(domains['dominios'])}; perfis: {len(profiles['perfis'])}; dispositivos: {len(devices['dispositivos'])}")
if devices['dispositivos']:
    name=quote(devices['dispositivos'][0]['id'],safe='')
    readings=get(f'/api/v1/dispositivos/{name}/telemetria?limite=10')
    assert isinstance(readings['dados'], list)
    print(f"[OK] Histórico de {devices['dispositivos'][0]['id']} consultado: {len(readings['dados'])} leituras")
print('[OK] Verificação somente-leitura concluída; não é homologação do MVP')
