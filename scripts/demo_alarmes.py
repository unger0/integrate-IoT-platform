"""Demonstração de ponta a ponta da v0.5.0 com dados SINTÉTICOS.

Cria 1 regra (idempotente pelo nome), gera, reconhece e normaliza um alarme.
Utiliza token demonstrativo se a API estiver em modo protegido.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8000'
TENANT='coop-cerrado'
DEVICE='solo-talhao07-02'
RULE='regra-demonstracao-v050'
TOKENFILE=ROOT/'runtime/token-gestor.txt'

def call(method, path, body=None, token=''):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    raw=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
    req=Request(BASE+path,data=raw,headers=headers,method=method)
    try:
        with urlopen(req,timeout=15) as resp:
            return resp.status,json.load(resp)
    except HTTPError as exc:
        try:payload=json.load(exc)
        except Exception:payload={'detail':exc.reason}
        return exc.code,payload

def must(statuses, response, label):
    code,data=response
    if code not in statuses:
        raise RuntimeError(f'{label}: HTTP {code}: {data}')
    return data

def main():
    health=must((200,),call('GET','/health'),'Health')
    if health.get('modo_protegido_demo'):
        if not TOKENFILE.is_file():
            raise RuntimeError('Token ausente; execute scripts/linux/09-iniciar-protegido.sh')
        token=TOKENFILE.read_text().strip()
    else:token=''
    from urllib.parse import quote
    q=quote(TENANT,safe='')
    must((200,201),call('POST','/api/v1/catalogo/dominios',{'inquilino':TENANT,'nome':'agricultura'},token),'Domínio')
    device_list=must((200,),call('GET',f'/api/v1/dispositivos?inquilino={q}',token=token),'Inventário')
    if not any(d['id']==DEVICE for d in device_list['dispositivos']):
        must((201,),call('POST','/api/v1/dispositivos',{
            'id':DEVICE,'inquilino':TENANT,'dominio':'agricultura',
            'site':'fazenda-boa-vista','area':'talhao-07'},token),'Cadastro sensor demo')
    spec={'inquilino':TENANT,'nome':RULE,'dispositivo':DEVICE,
          'grandeza':'umidade_solo','unidade':'%','operador':'maior_que',
          'limite':80,'severidade':'alta'}
    code,data=call('POST','/api/v1/regras',spec,token)
    if code not in (201,409): raise RuntimeError(f'Criar regra: HTTP {code}: {data}')
    print('[OK] Regra de umidade acima de 80% disponível')
    state=must((200,),call('GET',f'/api/v1/dispositivos/{DEVICE}/estado',token=token),'Último estado')
    now=datetime.now(timezone.utc)
    previous=[]
    for m in state.get('medidas',[]):
        if m['measurement_name']=='umidade_solo':
            previous.append(datetime.fromisoformat(m['measured_at'].replace('Z','+00:00')))
    base=max([now,*previous]) + timedelta(seconds=2)

    def submit(value, timestamp):
        msg={'versao':'1.0','id_mensagem':str(uuid.uuid4()),'dispositivo':DEVICE,
             'tipo':'telemetria','timestamp':timestamp.isoformat(),
             'medidas':[{'grandeza':'umidade_solo','valor':value,'unidade':'%'}]}
        ret=must((202,),call('POST','/api/v1/ingestao',msg,token),'Ingestão')
        if ret['status'] != 'aceita': raise RuntimeError(f'Mensagem não foi aceita: {ret}')
    submit(92,base)
    alarms=must((200,),call('GET',f'/api/v1/alarmes?inquilino={q}&limite=500',token=token),'Alarmes')['alarmes']
    selected=next((a for a in alarms if a['rule_name']==RULE and a['status']=='ativo'),None)
    if not selected: raise RuntimeError('Alarme ativo não encontrado após leitura 92%')
    aid=selected['id']
    print(f'[OK] Alarme #{aid} ativo após leitura sintética 92%')
    must((200,),call('POST',f'/api/v1/alarmes/{aid}/reconhecer',{'inquilino':TENANT},token),'Reconhecer')
    print('[OK] Alarme reconhecido')
    # Medição anterior não pode apagar alarme mais recente.
    submit(42,base-timedelta(seconds=1))
    alarms=must((200,),call('GET',f'/api/v1/alarmes?inquilino={q}&limite=500',token=token),'Reconsultar')['alarmes']
    item=next(a for a in alarms if a['id']==aid)
    if item['status']!='reconhecido':raise RuntimeError('Medição atrasada alterou indevidamente o alarme')
    print('[OK] Medição atrasada não alterou alarme atual')
    submit(42,base+timedelta(seconds=1))
    alarms=must((200,),call('GET',f'/api/v1/alarmes?inquilino={q}&limite=500',token=token),'Alarme normalizado')['alarmes']
    item=next(a for a in alarms if a['id']==aid)
    if item['status']!='resolvido' or item['resolved_reason']!='normalizado':
        raise RuntimeError('Alarme não foi automaticamente resolvido')
    print('[OK] Nova leitura 42% resolveu o alarme automaticamente')
    print('[OK] Fluxo completo demonstrado com dados sintéticos; não homologa RF-PRO-02/03/05 nem RNFs.')

if __name__=='__main__':main()
