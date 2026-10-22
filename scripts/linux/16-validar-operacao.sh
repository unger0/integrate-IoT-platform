#!/usr/bin/env bash
# Validação SOMENTE-LEITURA: consulta o diagnóstico de dispositivos da organização.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python - <<'PY'
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
import json,sys
base='http://127.0.0.1:8000'
root=Path.cwd()

def get(path, token=None):
    headers={'Authorization': 'Bearer '+token} if token else {}
    with urlopen(Request(base+path,headers=headers),timeout=5) as response:
        return json.load(response)

try:
    health=get('/health')
    if health.get('status')!='ok':raise ValueError('status de saúde inesperado')
    print('[OK] API respondeu; modo protegido demonstrativo:',health.get('modo_protegido_demo'))
    token=None
    tenant='coop-cerrado'
    if health.get('modo_protegido_demo'):
        file=root/'runtime/token-gestor.txt'
        if not file.is_file():
            sys.exit('[ERRO] Token local ausente. Use scripts/linux/15-renovar-token-gestor.sh')
        token=file.read_text().strip()
        identity=get('/api/v1/identidade',token)
        if not identity.get('autenticado'):
            sys.exit('[ERRO] Token não autenticado')
        tenant=identity['inquilino']
        print('[OK] Token validado para a organização:',tenant)
    data=get('/api/v1/operacao/dispositivos?'+urlencode({'inquilino':tenant,'limite':500}),token)
    allowed={'em_dia','atrasado','sem_dados','sem_perfil','relogio_inconsistente'}
    assert data['inquilino']==tenant
    assert data['total_retorno']==len(data['dispositivos'])
    assert all(d['estado'] in allowed for d in data['dispositivos'])
    assert sum(data['contagens'].values())==len(data['dispositivos'])
    print('[OK] Diagnóstico da organização:',tenant)
    for state,n in data['contagens'].items():
        print('   -',state+':',n)
    if data.get('amostra_limitada'):
        print('[ATENÇÃO] Limite de 500 atingido. Resultado é uma amostra, não o inventário completo.')
    print('[OK] Consulta somente-leitura concluída. Não é homologação do RF-DIS-06.')
except HTTPError as exc:
    if exc.code==401:
        sys.exit('[ERRO] Token expirado/inválido. Execute ./scripts/linux/15-renovar-token-gestor.sh')
    if exc.code==403:
        sys.exit('[ERRO] Sem permissão para esta organização.')
    sys.exit(f'[ERRO] HTTP {exc.code} consultando a API.')
except (URLError,OSError,TimeoutError,ValueError,AssertionError) as exc:
    sys.exit(f'[ERRO] Verificação não concluída: {exc}')
PY
