"""Fila offline DIDÁTICA. O conteúdo SQLite NÃO está cifrado: RF-SEG-05/RNF-11 pendentes.
Não expor a rede externa; não usar em produção.
"""
import os,sqlite3,json,asyncio
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from fastapi import FastAPI
import httpx

SQLITE=Path(os.environ.get('SQLITE_PATH','/tmp/edge-lab.sqlite'))
URL=os.environ.get('CENTRAL_URL','http://localhost:8000/api/v1/ingestao/lote')
INTERVAL=int(os.environ.get('SYNC_INTERVAL_SECONDS','8'))

@contextmanager
def connection():
    conn=sqlite3.connect(SQLITE,timeout=15)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=FULL')
        with conn:
            yield conn
    finally:
        conn.close()

def setup():
    SQLITE.parent.mkdir(parents=True,exist_ok=True)
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS queue (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

def enqueue(data):
    # Ainda falta validar JSON Schema, autenticação, ACL e criptografia.
    message_id=data.get('id_mensagem')
    if not isinstance(message_id,str) or not message_id:
        return False
    with connection() as db:
        db.execute('INSERT OR IGNORE INTO queue(id,payload) VALUES (?,?)',(message_id,json.dumps(data,ensure_ascii=False)))
    return True

def pending():
    with connection() as db:
        rows=db.execute('SELECT id,payload FROM queue ORDER BY rowid LIMIT 100').fetchall()
    return [(rid,json.loads(payload)) for rid,payload in rows]

def forget(ids):
    with connection() as db:
        db.executemany('DELETE FROM queue WHERE id=?',[(rid,) for rid in ids])

def count():
    with connection() as db:
        return db.execute('SELECT count(*) FROM queue').fetchone()[0]

async def sync_once():
    rows=pending()
    if not rows:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response=await client.post(URL,json=[item for rid,item in rows])
            response.raise_for_status()
            result=response.json()
        confirmed=[]
        for entry in result.get('resultados',[]):
            i=entry.get('indice')
            if isinstance(i,int) and 0<=i<len(rows) and entry.get('status') in ('aceita','duplicada'):
                confirmed.append(rows[i][0])
        forget(confirmed)
    except (httpx.HTTPError,ValueError,KeyError) as exc:
        print('Central inacessível ou erro de lote: fila preservada:',exc,flush=True)

async def sync_loop():
    while True:
        await sync_once()
        await asyncio.sleep(INTERVAL)

@asynccontextmanager
async def lifespan(app:FastAPI):
    setup()
    task=asyncio.create_task(sync_loop())
    yield
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass

app=FastAPI(title='Nó de Borda — LABORATÓRIO', lifespan=lifespan)

@app.get('/health')
def health():return {'status':'ok','fila':count(),'aviso':'fila em texto claro / sem auth / não produção'}

@app.get('/fila')
def queue_status():return {'pendentes':count()}

@app.post('/api/v1/ingestao',status_code=202)
def ingest(data:dict):
    if not enqueue(data):
        from fastapi import HTTPException
        raise HTTPException(status_code=400,detail='id_mensagem obrigatório')
    return {'status':'enfileirada','pendentes':count()}

@app.post('/sincronizar')
async def sync():
    await sync_once()
    return {'pendentes':count()}
