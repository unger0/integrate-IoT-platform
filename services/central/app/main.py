"""Fatia didática. SEM OIDC, MFA, RBAC, MQTT-TLS, isolamento autorizado ou DLQ.
Não disponibilize externamente nem use com telemetria real.
"""
import json
from contextlib import asynccontextmanager
from time import perf_counter
from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, HTTPException, Query, Request, Depends, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from .db import initialize, connection
from .schemas import Telemetria, NovoDispositivo, NovoDominio, NovoPerfil, VinculoPerfil, RegraLimiar, AcaoAlarme
from .profile_rules import avaliar_medida
from .threshold_rules import violated, can_evaluate
from .device_status import avaliar_pontualidade
from . import auth_demo as auth
from . import observability as obs

@asynccontextmanager
async def lifespan(app: FastAPI):
    if auth.enabled():
        auth.validate_secret()
    initialize()
    yield

app = FastAPI(title='Plataforma IoT Integrada — LABORATÓRIO', version='0.7.0', lifespan=lifespan, dependencies=[Depends(auth.authenticate)])
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['GET','POST','PUT'], allow_headers=['*'])

@app.middleware('http')
async def observability_middleware(request: Request, call_next):
    correlation = obs.correlation_for_header(request.headers.get('X-Correlation-ID'))
    marker = obs.CORRELATION.set(correlation)
    started = perf_counter()
    status = 500
    response = None
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers['X-Correlation-ID'] = correlation
        return response
    finally:
        route = request.scope.get('route')
        template = getattr(route, 'path', 'unmatched')
        obs.track_http(request.method, template, status, started)
        obs.CORRELATION.reset(marker)


@app.get('/metrics', include_in_schema=False)
def metrics():
    # Metricas globais revelam trafego de outras organizacoes: no modo JWT, apenas admin.
    auth.require_roles('administrador')
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get('/api/v1/observabilidade/resumo')
def obs_summary(inquilino: str = Query(min_length=1)):
    # Resumo persistido POR ORGANIZACAO (nao exibe contadores HTTP globais).
    auth.require_tenant(inquilino, 'administrador', 'gestor', 'operador', 'integrador', 'leitor')
    with connection() as conn:
        mensagens = conn.execute("""SELECT COUNT(*) AS total, MAX(received_at) AS ultima
                   FROM telemetry_messages WHERE tenant_id=%s""", (inquilino,)).fetchone()
        qualidades = conn.execute("""SELECT quality, COUNT(*) AS total
                   FROM measurements WHERE tenant_id=%s GROUP BY quality""", (inquilino,)).fetchall()
        alarmes = conn.execute("""SELECT COUNT(*) AS total FROM alarms WHERE tenant_id=%s
                   AND status IN ('ativo','reconhecido')""", (inquilino,)).fetchone()
    return {
        'inquilino': inquilino,
        'mensagens_persistidas': mensagens['total'],
        'ultima_recepcao': mensagens['ultima'].isoformat() if mensagens['ultima'] else None,
        'classificacoes': {k: next((r['total'] for r in qualidades if r['quality']==k), 0)
                           for k in ('conforme','suspeita','nao_avaliada')},
        'alarmes_abertos': alarmes['total'],
        'aviso': 'Contagem historica persistida desta organizacao; nao inclui duplicatas rejeitadas. '
                 'Contadores HTTP Prometheus sao globais e reiniciam com a API.',
    }


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith('/api/v1/ingestao'):
        obs.track_telemetry('lote' if request.url.path.endswith('/lote') else 'http', 'recusada')
        return JSONResponse(status_code=400, content={'erros': [str(e['loc'])+': '+e['msg'] for e in exc.errors()]})
    return JSONResponse(status_code=422, content={'erros': [str(e['loc'])+': '+e['msg'] for e in exc.errors()]})

@app.get('/health')
def health():
    return {'status':'ok', 'modo_protegido_demo':auth.enabled(),
            'aviso':'Somente laboratório local. Não há OIDC, MFA, TLS ou segurança de produção.'}

@app.get('/api/v1/identidade')
def identity():
    p = auth.require_roles('administrador','gestor','operador','integrador','leitor','borda','dispositivo')
    if p is None:
        return {'autenticado':False,'modo':'laboratorio'}
    return {'autenticado':True,'inquilino':p.tenant,'papel':p.role,'sujeito':p.subject}

@app.post('/api/v1/catalogo/dominios', status_code=201)
def add_domain(d: NovoDominio):
    auth.require_tenant(d.inquilino, 'administrador', 'gestor')
    with connection() as conn:
        conn.execute('INSERT INTO domains(tenant_id,name) VALUES (%s,%s) ON CONFLICT DO NOTHING', (d.inquilino,d.nome))
    return {'inquilino':d.inquilino,'dominio':d.nome}

@app.get('/api/v1/catalogo/dominios')
def list_domains(inquilino: str = Query(min_length=1)):
    auth.require_tenant(inquilino, 'administrador','gestor','operador','integrador','leitor')
    """Inventário configurável; filtro é didático, NÃO controle de acesso."""
    with connection() as conn:
        rows = conn.execute('''SELECT name FROM domains
                               WHERE tenant_id=%s ORDER BY name''',
                            (inquilino,)).fetchall()
    return {'inquilino': inquilino, 'dominios': [r['name'] for r in rows]}


@app.post('/api/v1/catalogo/perfis', status_code=201)
def add_profile(perfil: NovoPerfil):
    auth.require_tenant(perfil.inquilino, 'administrador','gestor')
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
    auth.require_tenant(inquilino, 'administrador','gestor','operador','integrador','leitor')
    with connection() as conn:
        profiles = conn.execute("""SELECT name, domain, expected_interval_seconds
                                  FROM device_profiles WHERE tenant_id=%s ORDER BY name""",
                               (inquilino,)).fetchall()
    return {'inquilino': inquilino, 'perfis': profiles}


@app.get('/api/v1/catalogo/perfis/{inquilino}/{nome}')
def get_profile(inquilino: str, nome: str):
    auth.require_tenant(inquilino, 'administrador','gestor','operador','integrador','leitor')
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
    auth.require_tenant(inquilino, 'administrador','gestor','operador','integrador','leitor')
    """Lista dispositivos por organização declarada (laboratório sem autorização)."""
    with connection() as conn:
        devices = conn.execute('''SELECT id, tenant_id, domain, site, area,
                                        profile_name, manufacturer, firmware
                                 FROM devices WHERE tenant_id=%s
                                 ORDER BY id LIMIT %s''',
                               (inquilino, limite)).fetchall()
    return {'inquilino': inquilino, 'total_retorno': len(devices), 'dispositivos': devices}


@app.get('/api/v1/operacao/dispositivos')
def device_freshness(inquilino: str = Query(min_length=1),
                     limite: int = Query(default=500, ge=1, le=500)):
    """Status estimado com base no horário de medição e intervalo do perfil.

    Não atesta conexão MQTT; perfis com uma hora de intervalo não ficam atrasados
    após cinco minutos. Consulta é somente-leitura e respeita o token/tenant no
    modo JWT demonstrativo.
    """
    auth.require_tenant(inquilino, 'administrador','gestor','operador','integrador','leitor')
    agora = datetime.now(timezone.utc)
    with connection() as conn:
        rows = conn.execute("""SELECT d.id, d.domain, d.site, d.area, d.profile_name,
                        p.expected_interval_seconds,
                        ultima.last_measured_at
                  FROM devices d
                  LEFT JOIN device_profiles p
                    ON p.tenant_id=d.tenant_id AND p.name=d.profile_name
                  LEFT JOIN LATERAL (
                    SELECT MAX(measured_at) AS last_measured_at
                    FROM last_state WHERE device_id=d.id
                  ) ultima ON TRUE
                  WHERE d.tenant_id=%s ORDER BY d.id LIMIT %s""",
                  (inquilino,limite)).fetchall()
    result = []
    for row in rows:
        data = avaliar_pontualidade(row['last_measured_at'],
                                    row['expected_interval_seconds'], agora)
        result.append({**row, 'last_measured_at': row['last_measured_at'].isoformat()
                       if row['last_measured_at'] is not None else None, **data})
    estados = ('em_dia','atrasado','sem_dados','sem_perfil','relogio_inconsistente')
    return {'inquilino': inquilino, 'calculado_em': agora.isoformat(),
            'amostra_limitada': len(result) == limite,
            'total_retorno': len(result),
            'contagens': {estado: sum(d['estado']==estado for d in result) for estado in estados},
            'dispositivos': result}


@app.post('/api/v1/dispositivos', status_code=201)
def add_device(d: NovoDispositivo):
    auth.require_tenant(d.inquilino, 'administrador','gestor','integrador')
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
    auth.require_tenant(vinculo.inquilino, 'administrador','gestor')
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


def _actor() -> str:
    principal = auth.current()
    return principal.subject if principal else 'laboratorio-local'


def process_threshold_alarms(conn, tenant: str, device_id: str, measure, measured_at: datetime):
    """Executado na mesma transação da medição; somente limiares de dispositivo.

    Não aciona dispositivos. Medições anteriores ao último estado são ignoradas no chamador.
    """
    rules = conn.execute("""SELECT id, threshold, operator, severity FROM threshold_rules
        WHERE tenant_id=%s AND device_id=%s AND measurement_name=%s
          AND unit=%s AND enabled=TRUE ORDER BY id""",
        (tenant, device_id, measure.grandeza, measure.unidade)).fetchall()
    for rule in rules:
        open_alarm = conn.execute("""SELECT id, status FROM alarms
            WHERE rule_id=%s AND device_id=%s AND status IN ('ativo','reconhecido')
            FOR UPDATE""", (rule['id'], device_id)).fetchone()
        if violated(measure.valor, rule['operator'], rule['threshold']):
            if open_alarm:
                conn.execute("""UPDATE alarms SET last_value=%s, last_measured_at=%s,
                    occurrences=occurrences+1 WHERE id=%s""",
                    (measure.valor, measured_at, open_alarm['id']))
            else:
                created = conn.execute("""INSERT INTO alarms
                    (rule_id, device_id, tenant_id, severity, status, initial_value,
                     last_value, unit, first_measured_at, last_measured_at)
                    VALUES (%s,%s,%s,%s,'ativo',%s,%s,%s,%s,%s) RETURNING id""",
                    (rule['id'], device_id, tenant, rule['severity'], measure.valor,
                     measure.valor, measure.unidade, measured_at, measured_at)).fetchone()
                conn.execute("""INSERT INTO alarm_events(alarm_id,event_type,actor)
                    VALUES (%s,'gerado','motor-de-regras')""", (created['id'],))
        elif open_alarm:
            conn.execute("""UPDATE alarms SET status='resolvido', resolved_at=NOW(),
                resolved_reason='normalizado', last_value=%s, last_measured_at=%s WHERE id=%s""",
                (measure.valor, measured_at, open_alarm['id']))
            conn.execute("""INSERT INTO alarm_events(alarm_id,event_type,actor)
                VALUES (%s,'resolvido_automaticamente','motor-de-regras')""",(open_alarm['id'],))


@app.post('/api/v1/regras', status_code=201)
def create_threshold_rule(regra: RegraLimiar):
    auth.require_tenant(regra.inquilino, 'administrador', 'gestor')
    with connection() as conn:
        device = conn.execute('SELECT id FROM devices WHERE id=%s AND tenant_id=%s',
                              (regra.dispositivo,regra.inquilino)).fetchone()
        if not device:
            raise HTTPException(404, detail='dispositivo não pertence à organização')
        exists = conn.execute('SELECT id FROM threshold_rules WHERE tenant_id=%s AND name=%s',
                              (regra.inquilino, regra.nome)).fetchone()
        if exists:
            raise HTTPException(409, detail='já existe uma regra com esse nome')
        result = conn.execute("""INSERT INTO threshold_rules
            (tenant_id, name, device_id, measurement_name, unit, operator, threshold, severity)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (regra.inquilino,regra.nome,regra.dispositivo,regra.grandeza,
             regra.unidade,regra.operador,regra.limite,regra.severidade)).fetchone()
    return {'id':result['id'],'nome':regra.nome,'aviso':'somente alarme interno; não comanda atuadores'}


@app.get('/api/v1/regras')
def list_threshold_rules(inquilino: str = Query(min_length=1)):
    auth.require_tenant(inquilino, 'administrador','gestor','operador','integrador','leitor')
    with connection() as conn:
        rows = conn.execute("""SELECT id, name, device_id, measurement_name, unit,
            operator, threshold, severity, enabled, created_at FROM threshold_rules
            WHERE tenant_id=%s ORDER BY id DESC LIMIT 200""", (inquilino,)).fetchall()
    return {'inquilino':inquilino,'regras':[{**r,'created_at':r['created_at'].isoformat()} for r in rows]}


@app.get('/api/v1/alarmes')
def list_alarms(inquilino: str = Query(min_length=1),
                status: str | None = Query(default=None, pattern='^(ativo|reconhecido|resolvido)$'),
                limite: int = Query(default=100, ge=1, le=500)):
    auth.require_tenant(inquilino, 'administrador','gestor','operador','integrador','leitor')
    with connection() as conn:
        rows = conn.execute("""SELECT a.id,a.device_id,a.severity,a.status,a.initial_value,
            a.last_value,a.unit,a.occurrences,a.first_measured_at,a.last_measured_at,
            a.acknowledged_at,a.resolved_at,a.resolved_reason, r.name AS rule_name,
            r.measurement_name,r.operator,r.threshold FROM alarms a
            JOIN threshold_rules r ON r.id=a.rule_id
            WHERE a.tenant_id=%s AND (%s::text IS NULL OR a.status=%s)
            ORDER BY a.created_at DESC LIMIT %s""",
            (inquilino,status,status,limite)).fetchall()
    return {'inquilino':inquilino,'alarmes':[
        {k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in row.items()}
        for row in rows]}


@app.post('/api/v1/alarmes/{alarm_id}/reconhecer')
def acknowledge_alarm(alarm_id: int, body: AcaoAlarme):
    auth.require_tenant(body.inquilino, 'administrador','gestor','operador')
    with connection() as conn:
        alarm = conn.execute('SELECT status FROM alarms WHERE id=%s AND tenant_id=%s FOR UPDATE',
                             (alarm_id,body.inquilino)).fetchone()
        if not alarm:
            raise HTTPException(404, detail='alarme não encontrado nesta organização')
        if alarm['status'] != 'ativo':
            raise HTTPException(409, detail='somente um alarme ativo pode ser reconhecido')
        conn.execute("""UPDATE alarms SET status='reconhecido',acknowledged_at=NOW()
                      WHERE id=%s""",(alarm_id,))
        conn.execute("""INSERT INTO alarm_events(alarm_id,event_type,actor)
                      VALUES (%s,'reconhecido',%s)""",(alarm_id,_actor()))
    return {'id':alarm_id,'status':'reconhecido'}


@app.post('/api/v1/alarmes/{alarm_id}/resolver')
def resolve_alarm(alarm_id: int, body: AcaoAlarme):
    auth.require_tenant(body.inquilino, 'administrador','gestor','operador')
    with connection() as conn:
        alarm = conn.execute('SELECT status FROM alarms WHERE id=%s AND tenant_id=%s FOR UPDATE',
                             (alarm_id,body.inquilino)).fetchone()
        if not alarm:
            raise HTTPException(404, detail='alarme não encontrado nesta organização')
        if alarm['status'] == 'resolvido':
            raise HTTPException(409, detail='alarme já está resolvido')
        conn.execute("""UPDATE alarms SET status='resolvido',resolved_at=NOW(),
                      resolved_reason='manual' WHERE id=%s""",(alarm_id,))
        conn.execute("""INSERT INTO alarm_events(alarm_id,event_type,actor)
                      VALUES (%s,'resolvido_manualmente',%s)""",(alarm_id,_actor()))
    return {'id':alarm_id,'status':'resolvido', 'aviso':'nova leitura acima do limite poderá gerar outro alarme'}


def save_one(msg: Telemetria) -> str:
    # Idempotência HTTP central, não garante durabilidade do caminho MQTT end-to-end.
    with connection() as conn:
        # Serializa ingestões do mesmo dispositivo para evitar alarmes abertos concorrentes.
        device=conn.execute('SELECT tenant_id, profile_name FROM devices WHERE id=%s FOR UPDATE',(msg.dispositivo,)).fetchone()
        if not device:
            raise ValueError('dispositivo não cadastrado')
        auth.require_device(device['tenant_id'], msg.dispositivo, 'administrador','gestor','integrador','borda','dispositivo')
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
            # Antes de alterar last_state, verifica se esta medição é a mais recente.
            # Dados antigos permanecem no histórico sem disparar alarmes "atuais".
            anterior = conn.execute("""SELECT measured_at FROM last_state
                WHERE device_id=%s AND measurement_name=%s""",
                (msg.dispositivo, measure.grandeza)).fetchone()
            eh_atual = can_evaluate(msg.timestamp, anterior['measured_at'] if anterior else None)
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
            if eh_atual:
                process_threshold_alarms(conn, device['tenant_id'], msg.dispositivo,
                                         measure, msg.timestamp)
    return 'aceita'

@app.post('/api/v1/ingestao',status_code=202)
def ingest(msg: Telemetria):
    try:
        result=save_one(msg)
    except (ValueError, HTTPException) as e:
        obs.track_telemetry('http', 'recusada', str(msg.id_mensagem))
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(400,detail=str(e)) from e
    obs.track_telemetry('http', result, str(msg.id_mensagem))
    return {'id_mensagem':str(msg.id_mensagem),'status':result}

@app.post('/api/v1/ingestao/lote')
def ingest_batch(payload: list[dict[str,Any]]):
    # Iteração simples: ainda falta validação contra JSON Schema versionado, DLQ e desempenho de 5 mil entradas.
    results=[]
    for i,raw in enumerate(payload):
        try:
            m=Telemetria.model_validate(raw)
            status=save_one(m)
            obs.track_telemetry('lote', status, str(m.id_mensagem))
            results.append({'indice':i,'id_mensagem':str(m.id_mensagem),'status':status})
        except (ValidationError,ValueError,HTTPException) as exc:
            obs.track_telemetry('lote', 'recusada')
            results.append({'indice':i,'status':'recusada','erro':str(exc)})
    return {'aceitas':sum(x['status']=='aceita' for x in results),
            'duplicadas':sum(x['status']=='duplicada' for x in results),
            'recusadas':sum(x['status']=='recusada' for x in results),
            'resultados':results}

@app.get('/api/v1/dispositivos/{id}/telemetria')
def history(id:str, grandeza:str|None=None, limite:int=Query(100,ge=1,le=1000)):
    auth.require_roles('administrador','gestor','operador','integrador','leitor')
    with connection() as conn:
        if auth.enabled():
            device = conn.execute('SELECT tenant_id FROM devices WHERE id=%s', (id,)).fetchone()
            if not device:
                raise HTTPException(404, detail='dispositivo não encontrado')
            auth.require_tenant(device['tenant_id'], 'administrador','gestor','operador','integrador','leitor')
        rows=conn.execute("""SELECT message_id, measured_at, measurement_name, value, unit, quality, quality_reason FROM measurements
           WHERE device_id=%s AND (%s::text IS NULL OR measurement_name=%s)
           ORDER BY measured_at DESC LIMIT %s""",(id,grandeza,grandeza,limite)).fetchall()
    return {'dispositivo':id,'total_retorno':len(rows),'dados':[{**x,'message_id':str(x['message_id']),'measured_at':x['measured_at'].isoformat()} for x in rows]}

@app.get('/api/v1/dispositivos/{id}/estado')
def state(id:str):
    auth.require_roles('administrador','gestor','operador','integrador','leitor')
    with connection() as conn:
        if auth.enabled():
            device = conn.execute('SELECT tenant_id FROM devices WHERE id=%s', (id,)).fetchone()
            if not device:
                raise HTTPException(404, detail='dispositivo não encontrado')
            auth.require_tenant(device['tenant_id'], 'administrador','gestor','operador','integrador','leitor')
        rows=conn.execute('SELECT measurement_name,measured_at,value,unit,quality,quality_reason FROM last_state WHERE device_id=%s',(id,)).fetchall()
    return {'dispositivo':id,'medidas':[{**x,'measured_at':x['measured_at'].isoformat()} for x in rows]}
