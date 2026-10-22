"""Observabilidade de laboratório: métricas em memória e logs JSON sem payloads.

Não é um sistema de auditoria imutável ou rastreamento distribuído.
Os contadores reiniciam junto com o processo. Rótulos de métricas são limitados.
"""
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID, uuid4

from prometheus_client import Counter, Histogram

CORRELATION = ContextVar('iot_correlation_id', default='')
HTTP_REQUESTS = Counter(
    'iot_http_requests_total', 'Requisicoes HTTP da API central', ['method', 'route', 'status']
)
HTTP_LATENCY = Histogram(
    'iot_http_request_duration_seconds', 'Duracao das requisicoes HTTP na API central',
    ['method', 'route'], buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2, 5, 10)
)
TELEMETRY_RESULTS = Counter(
    'iot_telemetry_messages_total', 'Mensagens por resultado e canal de ingestao',
    ['channel', 'result']
)

LOGGER = logging.getLogger('iot.structured')
if not LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


def correlation_for_header(value: str | None) -> str:
    """Aceita somente UUID como correlação externa; nunca ecoa dados arbitrários."""
    if value:
        try:
            return str(UUID(value))
        except (TypeError, ValueError, AttributeError):
            pass
    return str(uuid4())


def log_event(event: str, **fields: object) -> None:
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'level': 'INFO',
        'component': 'api-central',
        'event': event,
        'correlation_id': CORRELATION.get() or None,
        **fields,
    }
    LOGGER.info(json.dumps(entry, ensure_ascii=False, separators=(',', ':'), default=str))


def track_http(method: str, route: str, status: int, started: float) -> None:
    # A rota é o template do FastAPI (ex. /dispositivos/{id}), nunca o caminho do usuário.
    duration = max(0.0, perf_counter() - started)
    HTTP_REQUESTS.labels(method, route, str(status)).inc()
    HTTP_LATENCY.labels(method, route).observe(duration)
    log_event('http_request', method=method, route=route, status=status,
              duration_ms=round(duration * 1000, 2))


def track_telemetry(channel: str, result: str, message_id: str | None = None) -> None:
    if channel not in {'http', 'lote'} or result not in {'aceita', 'duplicada', 'recusada'}:
        raise ValueError('rotulo de telemetria inesperado')
    TELEMETRY_RESULTS.labels(channel, result).inc()
    log_event('ingestao', channel=channel, result=result, message_id=message_id)
