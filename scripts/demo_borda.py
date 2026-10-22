"""Envia uma medição sintética à fila da borda, online ou offline."""
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json,uuid
endpoint='http://localhost:8001/api/v1/ingestao'
data={'versao':'1.0','id_mensagem':str(uuid.uuid4()),'dispositivo':'solo-talhao07-02','tipo':'telemetria',
 'timestamp':datetime.now(timezone.utc).isoformat(), 'via':'borda-fazenda-boa-vista',
 'local':{'site':'fazenda-boa-vista','area':'talhao-07'},
 'medidas':[{'grandeza':'umidade_solo','valor':23.5,'unidade':'%'},{'grandeza':'temperatura_solo','valor':21.8,'unidade':'Cel'}]}
req=Request(endpoint,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'},method='POST')
with urlopen(req,timeout=5) as r:print(r.status,r.read().decode())
print('Consulte http://localhost:8001/fila')
