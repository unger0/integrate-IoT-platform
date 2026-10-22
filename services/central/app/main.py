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
from .schemas import Telemetria, NovoDispositivo, NovoDominio, NovoPerfil, VinculoPerfil
from .profile_rules import avaliar_medida

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield

app = FastAPI(title='Plataforma IoT Integrada — LABORATÓRIO', version='0.3.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['GET','POST','PUT'], allow_headers=['*'])

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

@app.get('/api/v1/catalogo/dominios')
def list_domains(inquilino: str = Query(min_length=1)):
    """Inventário configurável; filtro é didático, NÃO controle de acesso."""
    with connection() as conn:
        rows = conn.execute('''SELECT name FROM domains
                               WHERE tenant_id=%s ORDER BY name''',
                            (inquilino,)).fetchall()
    return {'inquilino': inquilino, 'dominios': [r['name'] for r in rows]}


@app.post('/api/v1/catalogo/perfis', status_code=201)
def add_profile(perfil: NovoPerfil):
    """Criação por contrato, sem enumeração fixa de domínios ou grandezas."""
    with connection() as conn:
        dominio = conn.execute('SELECT name FROM domains WHERE tenant_id=%s AND name=%s',
                               (perfil.inquilino, perfil.dominio)).fetchone()
        if not dominio:
            raise HTTPException(400, detail='cadastre primeiro o domínio do perfil')
        ja_existe = conn.execute('SELECT name FROM device_profiles WHERE tenant_id=%s AND name=%s',
                                 (perfil.inquilino, perfil.nome)).fetchone()
        if ja_existe:
            raise HTTPException(409, detail='perfil já cadastrado para este inquilino')
        conn.execute("""INSERT INTO device_profiles(tenant_id,name,domain,expected_interval_seconds)
                        VALUES (%s,%s,%s,%s)""", (perfil.inquilino, perfil.nome,
                                                   perfil.dominio, perfil.intervalo_esperado_segundos))
        for grandeza in perfil.medidas:
            conn.execute("""INSERT INTO profile_measures
                          (tenant_id,profile_name,measurement_name,unit,minimum,maximum)
                          VALUES (%s,%s,%s,%s,%s,%s)""",
                         (perfil.inquilino, perfil.nome, grandeza.grandeza, grandeza.unidade,
                          grandeza.minimo, grandeza.maximo))
    return {'inquilino': perfil.inquilino, 'nome': perfil.nome, 'dominio': perfil.dominio,
            'intervalo_esperado_segundos': perfil.intervalo_esperado_segundos,
            'medidas': [m.model_dump() for m in perfil.medidas]}


@app.get('/api/v1/catalogo/perfis')
def list_profiles(inquilino: str = Query(min_length=1)):
    with connection() as conn:
        profiles = conn.execute("""SELECT name, domain, expected_interval_seconds
                                  FROM device_profiles WHERE tenant_id=%s ORDER BY name""",
                               (inquilino,)).fetchall()
    return {'inquilino': inquilino, 'perfis': profiles}


@app.get('/api/v1/catalogo/perfis/{inquilino}/{nome}')
def get_profile(inquilino: str, nome: str):
    with connection() as conn:
        profile = conn.execute("""SELECT tenant_id, name, domain, expected_interval_seconds
                                  FROM device_profiles WHERE tenant_id=%s AND name=%s""",
                               (inquilino, nome)).fetchone()
        if not profile:
            raise HTTPException(404, detail='perfil não encontrado')
        items = conn.execute("""SELECT measurement_name, unit, minimum, maximum
                                FROM profile_measures WHERE tenant_id=%s AND profile_name=%s
                                ORDER BY measurement_name""", (inquilino, nome)).fetchall()
    return {**profile, 'medidas': items}


@app.get('/api/v1/dispositivos')
def list_devices(inquilino: str = Query(min_length=1), limite: int = Query(100, ge=1, le=500)):
    """Lista dispositivos por organização declarada (laboratório sem autorização)."""
    with connection() as conn:
        devices = conn.execute('''SELECT id, tenant_id, domain, site, area,
                                        profile_name, manufacturer, firmware
                                 FROM devices WHERE tenant_id=%s
                                 ORDER BY id LIMIT %s''',
                               (inquilino, limite)).fetchall()
    return {'inquilino': inquilino, 'total_retorno': len(devices), 'dispositivos': devices}


@app.post('/api/v1/dispositivos', status_code=201)
def add_device(d: NovoDispositivo):
    with connection() as conn:
        found=conn.execute('SELECT id FROM devices WHERE id=%s', (d.id,)).fetchone()
        if found:
            raise HTTPException(status_code=409,detail='ID de dispositivo já cadastrado')
        if d.perfil:
            perfil = conn.execute('''SELECT domain FROM device_profiles
                                    WHERE tenant_id=%s AND name=%s''',
                                 (d.inquilino, d.perfil)).fetchone()
            if not perfil or perfil['domain'] != d.dominio:
                raise HTTPException(400, detail='perfil inexistente ou incompatível com inquilino/domínio')
        conn.execute('''INSERT INTO devices(id,tenant_id,domain,site,area,profile_name,manufacturer,firmware)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                     (d.id,d.inquilino,d.dominio,d.site,d.area,d.perfil,d.fabricante,d.firmware))
    return {'id':d.id,'perfil':d.perfil,
            'aviso':'Dispositivo de laboratório; credenciais não implementadas'}

@app.put('/api/v1/dispositivos/{id}/perfil')
def bind_profile(id: str, vinculo: VinculoPerfil):
    """Vincula um perfil a dispositivo já cadastrado (somente laboratório)."""
    with connection() as conn:
        device = conn.execute("""SELECT tenant_id, domain FROM devices
                                 WHERE id=%s AND tenant_id=%s""", (id, vinculo.inquilino)).fetchone()
        if not device:
            raise HTTPException(404, detail='dispositivo não encontrado neste inquilino')
        perfil = conn.execute("""SELECT domain FROM device_profiles
                                 WHERE tenant_id=%s AND name=%s""",
                              (vinculo.inquilino, vinculo.perfil)).fetchone()
        if not perfil or perfil['domain'] != device['domain']:
            raise HTTPException(400, detail='perfil inexistente ou incompatível com o domínio')
        conn.execute("""UPDATE devices SET profile_name=%s
                        WHERE id=%s AND tenant_id=%s""",
                     (vinculo.perfil, id, vinculo.inquilino))
    return {'dispositivo': id, 'perfil': vinculo.perfil,
            'aviso': 'leituras anteriores permanecem não avaliadas'}


def save_one(msg: Telemetria) -> str:
    # Idempotência HTTP central, não garante durabilidade do caminho MQTT end-to-end.
    with connection() as conn:
        device=conn.execute('SELECT tenant_id, profile_name FROM devices WHERE id=%s',(msg.dispositivo,)).fetchone()
        if not device:
            raise ValueError('dispositivo não cadastrado')
        regras = None
        if device['profile_name']:
            definicoes = conn.execute('''SELECT measurement_name,unit,minimum,maximum
                                        FROM profile_measures WHERE tenant_id=%s AND profile_name=%s''',
                                     (device['tenant_id'], device['profile_name'])).fetchall()
            regras = {d['measurement_name']: {'unidade': d['unit'], 'minimo': d['minimum'],
                                              'maximo': d['maximum']} for d in definicoes}
        result=conn.execute("""
            INSERT INTO telemetry_messages(message_id,device_id,tenant_id,measured_at,payload)
            VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING RETURNING message_id
        """,(msg.id_mensagem,msg.dispositivo,device['tenant_id'],msg.timestamp,msg.model_dump_json())).fetchone()
        if not result:
            return 'duplicada'
        for i,measure in enumerate(msg.medidas):
            qualidade, motivo = avaliar_medida(measure, regras)
            conn.execute("""INSERT INTO measurements
                (message_id,ordinal,device_id,tenant_id,measured_at,measurement_name,value,unit,quality,quality_reason)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (msg.id_mensagem,i,msg.dispositivo,device['tenant_id'],msg.timestamp,
                 measure.grandeza,measure.valor,measure.unidade,qualidade,motivo))
            conn.execute("""INSERT INTO last_state
                (device_id,measurement_name,measured_at,value,unit,quality,quality_reason)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (device_id,measurement_name) DO UPDATE SET
                  measured_at=EXCLUDED.measured_at,value=EXCLUDED.value,unit=EXCLUDED.unit,
                  quality=EXCLUDED.quality,quality_reason=EXCLUDED.quality_reason
                WHERE last_state.measured_at <= EXCLUDED.measured_at""",
                (msg.dispositivo,measure.grandeza,msg.timestamp,measure.valor,measure.unidade,qualidade,motivo))
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
        rows=conn.execute("""SELECT message_id, measured_at, measurement_name, value, unit, quality, quality_reason FROM measurements
           WHERE device_id=%s AND (%s::text IS NULL OR measurement_name=%s)
           ORDER BY measured_at DESC LIMIT %s""",(id,grandeza,grandeza,limite)).fetchall()
    return {'dispositivo':id,'total_retorno':len(rows),'dados':[{**x,'message_id':str(x['message_id']),'measured_at':x['measured_at'].isoformat()} for x in rows]}

@app.get('/api/v1/dispositivos/{id}/estado')
def state(id:str):
    with connection() as conn:
        rows=conn.execute('SELECT measurement_name,measured_at,value,unit,quality,quality_reason FROM last_state WHERE device_id=%s',(id,)).fetchall()
    return {'dispositivo':id,'medidas':[{**x,'measured_at':x['measured_at'].isoformat()} for x in rows]}
