#!/usr/bin/env bash
# Verificacao somente-leitura: resumo por organizacao e endpoint Prometheus restrito.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python - <<'PY'
import json, os, sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
root=Path.cwd()
base='http://127.0.0.1:8000'

def get(path, token=None):
    hdr={'Authorization': 'Bearer '+token} if token else {}
    with urlopen(Request(base+path,headers=hdr),timeout=6) as response:
        return response.read().decode()

try:
    health=json.loads(get('/health'))
    if health.get('status')!='ok': raise ValueError('health != ok')
    token=None
    tenant='coop-cerrado'
    protected=health.get('modo_protegido_demo',False)
    if protected:
        f=root/'runtime/token-gestor.txt'
        if not f.is_file():sys.exit('[ERRO] Token local ausente: use script 15-renovar-token-gestor.sh')
        token=f.read_text().strip()
        ident=json.loads(get('/api/v1/identidade',token))
        tenant=ident['inquilino']
        print('[OK] Identidade JWT:',tenant,'/ papel:',ident['papel'])
    doc=json.loads(get('/api/v1/observabilidade/resumo?'+urlencode({'inquilino':tenant}),token))
    assert doc['inquilino']==tenant
    assert doc['mensagens_persistidas']>=0
    assert set(doc['classificacoes'])=={'conforme','suspeita','nao_avaliada'}
    print('[OK] Mensagens persistidas:',doc['mensagens_persistidas'])
    print('[OK] Classificacoes:',doc['classificacoes'])
    print('[OK] Alarmes abertos:',doc['alarmes_abertos'])
    if protected:
        try:
            get('/metrics',token)
        except HTTPError as e:
            if e.code!=403:raise
            print('[OK] Token de gestor NAO pode consultar metricas globais (HTTP 403)')
        else:
            sys.exit('[ERRO] Gestor acessou metricas globais; deveria ser 403')
        secret_file=root/'.env.protegido'
        secret=next((l.split('=',1)[1].strip() for l in secret_file.read_text().splitlines()
                    if l.startswith('IOT_LAB_JWT_SECRET=')),None)
        if not secret:sys.exit('[ERRO] Chave local ausente')
        sys.path.insert(0,str(root/'scripts'))
        from gerar_token_lab import mint
        admin=mint(secret,'auditoria-local',tenant,'administrador',120)
        metrics=get('/metrics',admin)
    else:
        metrics=get('/metrics')
    assert 'iot_http_requests_total' in metrics
    assert 'iot_http_request_duration_seconds' in metrics
    assert 'iot_telemetry_messages_total' in metrics
    print('[OK] Exportacao Prometheus disponivel; metricas reiniciam junto com API.')
    print('[OK] Verificacao somente-leitura concluida, sem homologacao de observabilidade.')
except HTTPError as exc:
    if exc.code==401:sys.exit('[ERRO] Token expirado; execute script 15-renovar-token-gestor.sh')
    sys.exit(f'[ERRO] HTTP {exc.code} durante a validacao')
except (URLError, ValueError, KeyError, AssertionError, OSError) as exc:
    sys.exit(f'[ERRO] Falha ao validar observabilidade: {exc}')
PY
