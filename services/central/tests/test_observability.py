"""Observabilidade didática: segurança de acesso, correlação e contadores."""
import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient
from prometheus_client import generate_latest
from app.main import app
from app import observability as obs
from app.auth_demo import ISSUER, AUDIENCE
import jwt

SECRET = 'somente-testes-para-hmac-32bytes-ou-mais-2026'


def auth_headers(role='gestor', tenant='coop-cerrado'):
    now = int(datetime.now(timezone.utc).timestamp())
    token = jwt.encode({'iss': ISSUER, 'aud': AUDIENCE, 'sub': 'teste',
                        'tenant': tenant, 'role': role, 'iat': now, 'exp': now+300},
                       SECRET, algorithm='HS256')
    return {'Authorization': 'Bearer '+token}


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ, {'IOT_LAB_AUTH_MODE':'jwt', 'IOT_LAB_JWT_SECRET':SECRET})
        self.env.start()
        self.client=TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def test_correlation_is_uuid_not_untrusted_text(self):
        self.assertEqual(obs.correlation_for_header('123e4567-e89b-42d3-a456-426614174000'),
                         '123e4567-e89b-42d3-a456-426614174000')
        generated=obs.correlation_for_header('INJECTION\nAuthorization: Bearer secret')
        UUID(generated)
        self.assertNotIn('Bearer',generated)

    def test_header_and_prometheus_request_metric(self):
        response=self.client.get('/health', headers={'X-Correlation-ID':'not-an-uuid'})
        self.assertEqual(response.status_code,200)
        UUID(response.headers['X-Correlation-ID'])
        self.assertIn(b'iot_http_requests_total',generate_latest())

    def test_global_metrics_require_admin_in_protected_mode(self):
        self.assertEqual(self.client.get('/metrics').status_code,401)
        self.assertEqual(self.client.get('/metrics',headers=auth_headers()).status_code,403)
        result=self.client.get('/metrics',headers=auth_headers(role='administrador'))
        self.assertEqual(result.status_code,200)
        self.assertIn('iot_http_request_duration_seconds',result.text)
        self.assertIn('text/plain',result.headers['content-type'])

    def test_cross_tenant_summary_blocked_before_database(self):
        with patch('app.main.connection') as factory:
            response=self.client.get('/api/v1/observabilidade/resumo?inquilino=outro',
                                      headers=auth_headers())
            self.assertEqual(response.status_code,403)
            factory.assert_not_called()

    def test_summary_returns_scoped_historical_data(self):
        with patch('app.main.connection') as factory:
            conn=MagicMock()
            factory.return_value.__enter__.return_value=conn
            now=datetime.now(timezone.utc)
            conn.execute.return_value.fetchone.side_effect=[
                {'total': 9, 'ultima': now}, {'total': 1}
            ]
            conn.execute.return_value.fetchall.return_value=[
                {'quality':'conforme','total':7}, {'quality':'suspeita','total':2}
            ]
            response=self.client.get('/api/v1/observabilidade/resumo?inquilino=coop-cerrado',
                                     headers=auth_headers(role='leitor'))
            self.assertEqual(response.status_code,200)
            data=response.json()
            self.assertEqual(data['mensagens_persistidas'],9)
            self.assertEqual(data['classificacoes']['conforme'],7)
            self.assertEqual(data['classificacoes']['nao_avaliada'],0)
            self.assertEqual(data['alarmes_abertos'],1)
            for call in conn.execute.call_args_list:
                self.assertEqual(call.args[1],('coop-cerrado',))

    def test_structured_log_has_uuid_and_no_payload(self):
        token=obs.CORRELATION.set('123e4567-e89b-42d3-a456-426614174000')
        try:
            with patch.object(obs.LOGGER,'info') as emitted:
                obs.log_event('teste', status='ok')
                row=json.loads(emitted.call_args.args[0])
            self.assertEqual(row['correlation_id'],'123e4567-e89b-42d3-a456-426614174000')
            self.assertEqual(row['status'],'ok')
            self.assertNotIn('authorization',row)
        finally:
            obs.CORRELATION.reset(token)

    def test_ingestion_counts_unique_statuses(self):
        before=obs.TELEMETRY_RESULTS.labels('http','duplicada')._value.get()
        body={'versao':'1.0','id_mensagem':'123e4567-e89b-42d3-a456-426614174000',
              'dispositivo':'sensor-01','tipo':'telemetria','timestamp':'2026-10-22T12:00:00Z',
              'medidas':[{'grandeza':'umidade_solo','valor':25,'unidade':'%'}]}
        with patch('app.main.save_one',return_value='duplicada') as saved:
            resp=self.client.post('/api/v1/ingestao',json=body,headers=auth_headers())
            self.assertEqual(resp.status_code,202)
            self.assertEqual(resp.json()['status'],'duplicada')
            saved.assert_called_once()
        self.assertEqual(obs.TELEMETRY_RESULTS.labels('http','duplicada')._value.get(),before+1)

    def test_bad_schema_counts_rejection(self):
        before=obs.TELEMETRY_RESULTS.labels('http','recusada')._value.get()
        resp=self.client.post('/api/v1/ingestao',json={'foo':'bar'},headers=auth_headers())
        self.assertEqual(resp.status_code,400)
        self.assertEqual(obs.TELEMETRY_RESULTS.labels('http','recusada')._value.get(),before+1)


if __name__=='__main__':unittest.main()
