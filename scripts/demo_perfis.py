"""Demonstrar RF-CEN-02 na API 0.2.0 sem dependências locais externas.
Cria domínio/perfil, vincula ao sensor rural existente e testa 2 leituras.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API = 'http://127.0.0.1:8000'
INQUILINO = 'coop-cerrado'
PERFIL = 'solo-lab-v02'
DISPOSITIVO = 'solo-talhao07-02'

def requisitar(metodo: str, endpoint: str, corpo: dict | None = None):
    dados = None if corpo is None else json.dumps(corpo).encode('utf-8')
    req = Request(API + endpoint, method=metodo, data=dados,
                  headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        texto = exc.read().decode('utf-8', errors='replace')
        try:
            erro = json.loads(texto)
        except json.JSONDecodeError:
            erro = {'erro': texto}
        return exc.code, erro


def precisa(condicao, descricao):
    if not condicao:
        raise SystemExit('[ERRO] ' + descricao)
    print('[OK]', descricao)

status, _ = requisitar('POST', '/api/v1/catalogo/dominios',
                       {'inquilino': INQUILINO, 'nome': 'agricultura'})
precisa(status == 201, 'Domínio disponível')

perfil = {
    'inquilino': INQUILINO,
    'nome': PERFIL,
    'dominio': 'agricultura',
    'intervalo_esperado_segundos': 600,
    'medidas': [
        {'grandeza': 'umidade_solo', 'unidade': '%', 'minimo': 0, 'maximo': 100},
        {'grandeza': 'temperatura_solo', 'unidade': 'Cel', 'minimo': -10, 'maximo': 65},
    ],
}
status, corpo = requisitar('POST', '/api/v1/catalogo/perfis', perfil)
precisa(status in (201, 409), 'Perfil disponível (criado ou já existente)')
if status == 409:
    status, dados = requisitar('GET', f'/api/v1/catalogo/perfis/{INQUILINO}/{PERFIL}')
    precisa(status == 200 and dados['domain'] == perfil['dominio'] and
           dados['expected_interval_seconds'] == 600 and
           {m['measurement_name']:(m['unit'],m['minimum'],m['maximum']) for m in dados['medidas']} ==
           {m['grandeza']:(m['unidade'],m['minimo'],m['maximo']) for m in perfil['medidas']},
           'Perfil existente corresponde ao exemplo')

status, corpo = requisitar('PUT', f'/api/v1/dispositivos/{DISPOSITIVO}/perfil',
                         {'inquilino': INQUILINO, 'perfil': PERFIL})
precisa(status == 200, 'Perfil vinculado ao dispositivo rural: ' + str(corpo))

for valor, esperado in ((23.5, 'conforme'), (125, 'suspeita')):
    identificador = str(uuid.uuid4())
    mensagem = {'versao': '1.0', 'id_mensagem': identificador, 'dispositivo': DISPOSITIVO,
                'tipo': 'telemetria', 'timestamp': datetime.now(timezone.utc).isoformat(),
                'medidas': [{'grandeza': 'umidade_solo', 'valor': valor, 'unidade': '%'}]}
    status, corpo = requisitar('POST', '/api/v1/ingestao', mensagem)
    precisa(status == 202 and corpo.get('status') == 'aceita', f'Leitura {valor}% aceita na central')
    status, corpo = requisitar('GET', f'/api/v1/dispositivos/{DISPOSITIVO}/telemetria?limite=1000')
    precisa(status == 200, 'Histórico consultado')
    encontrada = next((r for r in corpo['dados'] if r['message_id'] == identificador), None)
    precisa(encontrada is not None and encontrada.get('quality') == esperado,
           f'Leitura {valor}% classificada como {esperado}')
    print('     Detalhe:', json.dumps({'qualidade': encontrada['quality'],
                                   'motivo': encontrada['quality_reason']}, ensure_ascii=False))

print('\n[OK] Perfis e classificação de qualidade demonstrados. Teste didático, não homologação de RF-CEN-02.')
