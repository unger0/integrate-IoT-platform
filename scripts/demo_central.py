"""Dados sintéticos: cadastro rural/urbano e envio direto do projeto urbano."""
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json,uuid
from datetime import datetime,timezone
API='http://localhost:8000'
def post(path,payload):
    req=Request(API+path,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urlopen(req,timeout=10) as r:print(path,r.status,r.read().decode()[:500])
    except HTTPError as e:
        if e.code==409:print('dispositivo já existia:',path)
        else:raise
for d in [
 {'id':'solo-talhao07-02','inquilino':'coop-cerrado','dominio':'agricultura','site':'fazenda-boa-vista','area':'talhao-07'},
 {'id':'ar-centro-03','inquilino':'semma','dominio':'ambiente','site':'centro','area':'praca'}]:
    post('/api/v1/dispositivos',d)
post('/api/v1/ingestao',{'versao':'1.0','id_mensagem':str(uuid.uuid4()),'dispositivo':'ar-centro-03','tipo':'telemetria','timestamp':datetime.now(timezone.utc).isoformat(), 'local':{'site':'centro','area':'praca'}, 'medidas':[{'grandeza':'pm25','valor':19.4,'unidade':'ug/m3'}]})
print('API Swagger:',API+'/docs')
