"""Avaliação de pontualidade + restrição de organização, sem banco de produção."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import jwt
from app.main import app
from app.device_status import avaliar_pontualidade
from app.auth_demo import ISSUER, AUDIENCE

T = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
SECRET = 'segredo-de-testes-local-e-suficientemente-longo-000000000'


class FreshnessPureTests(unittest.TestCase):
    def test_hourly_sensor_not_late_after_five_minutes(self):
        self.assertEqual(avaliar_pontualidade(T-timedelta(minutes=5),3600,T)['estado'], 'em_dia')

    def test_hourly_sensor_late_after_two_hours(self):
        self.assertEqual(avaliar_pontualidade(T-timedelta(hours=2,seconds=1),3600,T)['estado'], 'atrasado')

    def test_boundary_is_inclusive(self):
        self.assertEqual(avaliar_pontualidade(T-timedelta(hours=2),3600,T)['estado'], 'em_dia')

    def test_without_profile(self):
        self.assertEqual(avaliar_pontualidade(T-timedelta(minutes=1),None,T)['estado'], 'sem_perfil')

    def test_without_messages(self):
        self.assertEqual(avaliar_pontualidade(None,600,T)['estado'], 'sem_dados')

    def test_future_timestamp(self):
        self.assertEqual(avaliar_pontualidade(T+timedelta(minutes=6),600,T)['estado'], 'relogio_inconsistente')

    def test_small_clock_skew(self):
        self.assertEqual(avaliar_pontualidade(T+timedelta(minutes=1),600,T)['estado'], 'em_dia')

    def test_timezone_conversion(self):
        from datetime import timedelta as td
        local = T.astimezone(timezone(td(hours=-3)))
        self.assertEqual(avaliar_pontualidade(local,30,T)['estado'],'em_dia')

    def test_naive_time_is_rejected(self):
        with self.assertRaises(ValueError):
            avaliar_pontualidade(T.replace(tzinfo=None),600,T)


class FreshnessEndpointTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'IOT_LAB_AUTH_MODE':'jwt','IOT_LAB_JWT_SECRET':SECRET})
        self.env.start()
        self.client=TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def headers(self, tenant='coop-cerrado', role='gestor'):
        now=int(datetime.now(timezone.utc).timestamp())
        payload={'iss':ISSUER,'aud':AUDIENCE,'sub':'teste','tenant':tenant,'role':role,
                 'iat':now,'exp':now+300}
        if role=='dispositivo': payload['device_id']='sensor-a'
        return {'Authorization':'Bearer '+jwt.encode(payload,SECRET,algorithm='HS256')}

    def test_without_token_returns_401(self):
        self.assertEqual(self.client.get('/api/v1/operacao/dispositivos?inquilino=coop-cerrado').status_code,401)

    def test_other_tenant_denied_before_db(self):
        with patch('app.main.connection') as connection:
            result=self.client.get('/api/v1/operacao/dispositivos?inquilino=outro',headers=self.headers())
            self.assertEqual(result.status_code,403)
            connection.assert_not_called()

    def test_reader_can_view_own_tenant(self):
        with patch('app.main.connection') as factory:
            conn=MagicMock()
            factory.return_value.__enter__.return_value=conn
            conn.execute.return_value.fetchall.return_value=[
                {'id':'solo-1','domain':'agricultura','site':'fazenda','area':None,
                 'profile_name':'solo','expected_interval_seconds':3600,
                 'last_measured_at':datetime.now(timezone.utc)-timedelta(minutes=5)}]
            result=self.client.get('/api/v1/operacao/dispositivos?inquilino=coop-cerrado&limite=15',
                                   headers=self.headers(role='leitor'))
            self.assertEqual(result.status_code,200)
            doc=result.json()
            self.assertEqual(doc['total_retorno'],1)
            self.assertEqual(doc['contagens']['em_dia'],1)
            self.assertEqual(doc['dispositivos'][0]['estado'],'em_dia')
            sql,args=conn.execute.call_args.args
            self.assertIn('d.tenant_id=%s',sql)
            self.assertIn('LIMIT %s',sql)
            self.assertEqual(args,('coop-cerrado',15))

    def test_device_role_denied(self):
        with patch('app.main.connection') as factory:
            result=self.client.get('/api/v1/operacao/dispositivos?inquilino=coop-cerrado',
                                   headers=self.headers(role='dispositivo'))
            self.assertEqual(result.status_code,403)
            factory.assert_not_called()


if __name__ == '__main__':
    unittest.main()
