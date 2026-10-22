"""Ensaio de desconexão: para somente a API, preserva a fila e restaura a API.

Não representa teste de 72h, queda de rede física, nem segurança de produção.
Requer Docker/Compose acessíveis ao usuário, central/borda iniciadas e Python 3.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
CMD=['docker','compose','-f','infra/compose.lab.yml']
API='http://127.0.0.1:8000'
EDGE='http://127.0.0.1:8001'

def compose(*args):
    print('>', ' '.join(CMD+list(args)),flush=True)
    return subprocess.run(CMD+list(args),cwd=ROOT,check=True)

def get(url,timeout=3):
    with urlopen(url,timeout=timeout) as r:return json.load(r)

def post(url, data):
    req=Request(url,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urlopen(req,timeout=5) as r:return json.load(r)

def until(predicate,sec=60):
    end=time.monotonic()+sec
    while time.monotonic()<end:
        try:
            result=predicate()
            if result:return result
        except (OSError, URLError, ValueError):pass
        time.sleep(2)
    raise RuntimeError(f'Condição não atendida após {sec} segundos')


def main():
    print('TESTE ILUSTRATIVO: nenhuma alteração de redes/iptables; para somente a API do laboratório.')
    # Pré-requisitos: não interromper API se a borda estiver indisponível.
    get(API+'/health')
    get(EDGE+'/health')
    # Execução do script de cadastro é idempotente: 409 de dispositivo existente é tratado nele.
    subprocess.run([sys.executable,str(ROOT/'scripts/demo_central.py')], cwd=ROOT,check=True)
    before=get(EDGE+'/fila')['pendentes']
    id_msg=str(uuid4())
    message={
        'versao':'1.0','id_mensagem':id_msg, 'dispositivo':'solo-talhao07-02',
        'tipo':'telemetria','timestamp':datetime.now(timezone.utc).isoformat(),
        'via':'borda-archlinux-teste',
        'local':{'site':'fazenda-boa-vista','area':'talhao-07'},
        'medidas':[
            {'grandeza':'umidade_solo','valor':24.9,'unidade':'%'},
            {'grandeza':'temperatura_solo','valor':22.1,'unidade':'Cel'},
        ],
    }
    stopped=False
    try:
        compose('stop','api')
        stopped=True
        result=post(EDGE+'/api/v1/ingestao',message)
        print('[OK] Leitura enviada à borda durante a parada da API:',result)
        now=get(EDGE+'/fila')['pendentes']
        if now<=before:
            raise RuntimeError('Fila não cresceu durante a interrupção; examine outros produtores/sincronizadores.')
        print(f'[OK] Fila aumentou: antes={before} depois={now}')
    finally:
        if stopped:
            print('Restaurando obrigatoriamente a API central...')
            compose('start','api')
    until(lambda:get(API+'/health')['status']=='ok',sec=75)
    until(lambda:get(EDGE+'/fila')['pendentes']<=before,sec=75)
    def persisted():
        history=get(API+'/api/v1/dispositivos/solo-talhao07-02/telemetria?limite=1000')
        rows=[row for row in history.get('dados',[]) if row['message_id']==id_msg]
        return len(rows)==2 and len(set(row['measurement_name'] for row in rows))==2
    until(persisted,sec=60)
    print('[OK] Sincronização pós-reconexão e persistência das duas grandezas confirmadas para o UUID:',id_msg)
    print('Atenção: isto NÃO substitui testes de 72 horas, durabilidade, TLS e isolamento de acesso.')

if __name__=='__main__':
    try:main()
    except (subprocess.CalledProcessError, RuntimeError, OSError, URLError) as err:
        print('[ERRO]',err,file=sys.stderr)
        raise SystemExit(1)
