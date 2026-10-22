"""Testes sem banco real: proteção JWT demonstrativa por organização/papel.
NÃO equivalem aos testes OIDC/MFA exigidos no MVP.
"""
import os
import time
import unittest
from unittest.mock import patch, MagicMock
import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.auth_demo import ISSUER, AUDIENCE

SECRET = 'chave-de-teste-com-tamanho-suficiente-para-hmac-sha256-123'


def token(role='gestor', tenant='coop-cerrado', *, expired=False, device_id=None):
    now = int(time.time())
    payload={'iss':ISSUER,'aud':AUDIENCE,'sub':'tester','tenant':tenant,'role':role,
             'iat':now-300 if expired else now,'exp':now-100 if expired else now+300}
    if device_id:payload['device_id']=device_id
    return jwt.encode(payload, SECRET, algorithm='HS256')


class AuthDemoTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ, {'IOT_LAB_AUTH_MODE':'jwt','IOT_LAB_JWT_SECRET':SECRET})
        self.env.start()
        self.client=TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def test_health_public(self):
        r=self.client.get('/health')
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.json()['modo_protegido_demo'])

    def test_without_token_refused(self):
        self.assertEqual(self.client.get('/api/v1/identidade').status_code,401)
        self.assertEqual(self.client.get('/api/v1/dispositivos?inquilino=coop-cerrado').status_code,401)

    def test_invalid_and_expired_tokens_rejected(self):
        self.assertEqual(self.client.get('/api/v1/identidade', headers={'Authorization':'Bearer abc.def.ghi'}).status_code,401)
        self.assertEqual(self.client.get('/api/v1/identidade', headers={'Authorization':'Bearer '+token(expired=True)}).status_code,401)

    def test_valid_signed_token_identifies_tenant(self):
        resp=self.client.get('/api/v1/identidade',headers={'Authorization':'Bearer '+token()})
        self.assertEqual(resp.status_code,200)
        self.assertEqual(resp.json()['inquilino'],'coop-cerrado')

    def test_cross_tenant_denied_without_touching_database(self):
        with patch('app.main.connection') as conn:
            resp=self.client.get('/api/v1/dispositivos?inquilino=outro',headers={'Authorization':'Bearer '+token()})
            self.assertEqual(resp.status_code,403)
            conn.assert_not_called()

    def test_reader_cannot_create_domain(self):
        response=self.client.post('/api/v1/catalogo/dominios', json={'inquilino':'coop-cerrado','nome':'energia'},
                                  headers={'Authorization':'Bearer '+token(role='leitor')})
        self.assertEqual(response.status_code,403)

    def test_reader_can_list_own_domain(self):
        with patch('app.main.connection') as factory:
            cm=MagicMock()
            factory.return_value.__enter__.return_value=cm
            cm.execute.return_value.fetchall.return_value=[{'name':'agricultura'}]
            response=self.client.get('/api/v1/catalogo/dominios?inquilino=coop-cerrado',
                                     headers={'Authorization':'Bearer '+token(role='leitor')})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['dominios'],['agricultura'])

    def test_device_role_cannot_list_inventory(self):
        response=self.client.get('/api/v1/dispositivos?inquilino=coop-cerrado',
                                 headers={'Authorization':'Bearer '+token(role='dispositivo',device_id='sensor-a')})
        self.assertEqual(response.status_code,403)

    def test_other_tenant_history_rejected(self):
        with patch('app.main.connection') as factory:
            cm=MagicMock()
            factory.return_value.__enter__.return_value=cm
            cm.execute.return_value.fetchone.return_value={'tenant_id':'outro'}
            response=self.client.get('/api/v1/dispositivos/sensor-outro/telemetria',
                                     headers={'Authorization':'Bearer '+token(role='leitor')})
            self.assertEqual(response.status_code,403)

    def test_user_role_cannot_write_as_device(self):
        # leitor recebe bloqueio antes de qualquer tentativa de INSERT.
        data={'versao':'1.0','id_mensagem':'123e4567-e89b-42d3-a456-426614174000','dispositivo':'sensor-a',
              'tipo':'telemetria','timestamp':'2026-10-22T00:00:00Z',
              'medidas':[{'grandeza':'umidade_solo','valor':25,'unidade':'%'}]}
        with patch('app.main.connection') as factory:
            cm=MagicMock();factory.return_value.__enter__.return_value=cm
            cm.execute.return_value.fetchone.return_value={'tenant_id':'coop-cerrado','profile_name':None}
            response=self.client.post('/api/v1/ingestao',json=data,
                                      headers={'Authorization':'Bearer '+token(role='leitor')})
            self.assertEqual(response.status_code,403)


if __name__ == '__main__':unittest.main()
