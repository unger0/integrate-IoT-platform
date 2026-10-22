"""Fatia didática. SEM OIDC, MFA, RBAC, MQTT-TLS, isolamento autorizado ou DLQ.
Não disponibilize externamente nem use com telemetria real.
"""
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from .db import initialize, connection
from .schemas import Telemetria, NovoDispositivo, NovoDominio

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield

app = FastAPI(title='Plataforma IoT Integrada — LABORATÓRIO', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173'], allow_methods=['GET','POST'], allow_headers=['*'])

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith('/api/v1/ingestao'):
        return JSONResponse(status_code=400, content={'erros': [str(e['loc'])+': '+e['msg'] for e in exc.errors()]})
    return JSONResponse(status_code=422, content={'erros': [str(e['loc'])+': '+e['msg'] for e in exc.errors()]})

@app.get('/health')
def health():
    return {'status':'ok', 'aviso':'laboratório sem autenticação; NÃO produção'}

@app.post('/api/v1/catalogo/dominios', status_code=201)
def add_domain(d: NovoDominio):
    with connection() as conn:
        conn.execute('INSERT INTO domains(tenant_id,name) VALUES (%s,%s) ON CONFLICT DO NOTHING', (d.inquilino,d.nome))
    return {'inquilino':d.inquilino,'dominio':d.nome}

@app.post('/api/v1/dispositivos', status_code=201)
def add_device(d: NovoDispositivo):
    with connection() as conn:
        found=conn.execute('SELECT id FROM devices WHERE id=%s', (d.id,)).fetchone()
        if found:
            raise HTTPException(status_code=409,detail='ID de dispositivo já cadastrado')
        conn.execute('INSERT INTO devices(id,tenant_id,domain,site,area) VALUES (%s,%s,%s,%s,%s)',(d.id,d.inquilino,d.dominio,d.site,d.area))
    return {'id':d.id,'aviso':'Dispositivo de laboratório; credenciais não implementadas'}

def save_one(msg: Telemetria) -> str:
    # Idempotência HTTP central, não garante durabilidade do caminho MQTT end-to-end.
    with connection() as conn:
        device=conn.execute('SELECT tenant_id FROM devices WHERE id=%s',(msg.dispositivo,)).fetchone()
        if not device:
            raise ValueError('dispositivo não cadastrado')
        result=conn.execute("""
            INSERT INTO telemetry_messages(message_id,device_id,tenant_id,measured_at,payload)
            VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING RETURNING message_id
        """,(msg.id_mensagem,msg.dispositivo,device['tenant_id'],msg.timestamp,msg.model_dump_json())).fetchone()
        if not result:
            return 'duplicada'
        for i,measure in enumerate(msg.medidas):
            conn.execute("""INSERT INTO measurements(message_id,ordinal,device_id,tenant_id,measured_at,measurement_name,value,unit)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (msg.id_mensagem,i,msg.dispositivo,device['tenant_id'],msg.timestamp,measure.grandeza,measure.valor,measure.unidade))
            conn.execute("""INSERT INTO last_state(device_id,measurement_name,measured_at,value,unit)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (device_id,measurement_name) DO UPDATE SET
                  measured_at=EXCLUDED.measured_at,value=EXCLUDED.value,unit=EXCLUDED.unit
                WHERE last_state.measured_at <= EXCLUDED.measured_at""",
                (msg.dispositivo,measure.grandeza,msg.timestamp,measure.valor,measure.unidade))
    return 'aceita'

@app.post('/api/v1/ingestao',status_code=202)
def ingest(msg: Telemetria):
    try:
        result=save_one(msg)
    except ValueError as e:
        raise HTTPException(400,detail=str(e)) from e
    return {'id_mensagem':str(msg.id_mensagem),'status':result}

@app.post('/api/v1/ingestao/lote')
def ingest_batch(payload: list[dict[str,Any]]):
    # Iteração simples: ainda falta validação contra JSON Schema versionado, DLQ e desempenho de 5 mil entradas.
    results=[]
    for i,raw in enumerate(payload):
        try:
            m=Telemetria.model_validate(raw)
            status=save_one(m)
            results.append({'indice':i,'id_mensagem':str(m.id_mensagem),'status':status})
        except (ValidationError,ValueError) as exc:
            results.append({'indice':i,'status':'recusada','erro':str(exc)})
    return {'aceitas':sum(x['status']=='aceita' for x in results),
            'duplicadas':sum(x['status']=='duplicada' for x in results),
            'recusadas':sum(x['status']=='recusada' for x in results),
            'resultados':results}

@app.get('/api/v1/dispositivos/{id}/telemetria')
def history(id:str, grandeza:str|None=None, limite:int=Query(100,ge=1,le=1000)):
    with connection() as conn:
        rows=conn.execute("""SELECT message_id, measured_at, measurement_name, value, unit FROM measurements
           WHERE device_id=%s AND (%s::text IS NULL OR measurement_name=%s)
           ORDER BY measured_at DESC LIMIT %s""",(id,grandeza,grandeza,limite)).fetchall()
    return {'dispositivo':id,'total_retorno':len(rows),'dados':[{**x,'message_id':str(x['message_id']),'measured_at':x['measured_at'].isoformat()} for x in rows]}

@app.get('/api/v1/dispositivos/{id}/estado')
def state(id:str):
    with connection() as conn:
        rows=conn.execute('SELECT measurement_name,measured_at,value,unit FROM last_state WHERE device_id=%s',(id,)).fetchall()
    return {'dispositivo':id,'medidas':[{**x,'measured_at':x['measured_at'].isoformat()} for x in rows]}
