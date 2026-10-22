"""Testes de autorização das novas rotas, sem PostgreSQL real."""
import os
import time
import unittest
from unittest.mock import patch, MagicMock
import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.auth_demo import ISSUER, AUDIENCE

KEY='chave-do-teste-jwt-do-laboratorio-com-mais-de-32-bytes'
RULE={'inquilino':'coop-cerrado','nome':'regra','dispositivo':'sensor-1',
      'grandeza':'umidade_solo','unidade':'%','operador':'maior_que',
      'limite':80,'severidade':'alta'}

def signed(role='gestor', tenant='coop-cerrado'):
    now=int(time.time())
    return jwt.encode({'iss':ISSUER,'aud':AUDIENCE,'sub':'teste','tenant':tenant,
                       'role':role,'iat':now,'exp':now+300}, KEY, algorithm='HS256')

def headers(role='gestor', tenant='coop-cerrado'):
    return {'Authorization': 'Bearer '+signed(role,tenant)}

class AlarmAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'IOT_LAB_AUTH_MODE':'jwt','IOT_LAB_JWT_SECRET':KEY})
        self.env.start();self.client=TestClient(app)
    def tearDown(self):
        self.client.close();self.env.stop()

    def test_reader_cannot_create_rule(self):
        with patch('app.main.connection') as conn:
            r=self.client.post('/api/v1/regras',json=RULE,headers=headers('leitor'))
            self.assertEqual(r.status_code,403);conn.assert_not_called()

    def test_cross_tenant_cannot_list_alarms(self):
        with patch('app.main.connection') as conn:
            r=self.client.get('/api/v1/alarmes?inquilino=outro',headers=headers())
            self.assertEqual(r.status_code,403);conn.assert_not_called()

    def test_reader_can_list_own_alarms(self):
        with patch('app.main.connection') as factory:
            cm=MagicMock();factory.return_value.__enter__.return_value=cm
            cm.execute.return_value.fetchall.return_value=[]
            r=self.client.get('/api/v1/alarmes?inquilino=coop-cerrado',headers=headers('leitor'))
            self.assertEqual(r.status_code,200);self.assertEqual(r.json()['alarmes'],[])

    def test_reader_cannot_resolve(self):
        with patch('app.main.connection') as conn:
            r=self.client.post('/api/v1/alarmes/1/resolver',
                               json={'inquilino':'coop-cerrado'},headers=headers('leitor'))
            self.assertEqual(r.status_code,403);conn.assert_not_called()

    def test_reader_cannot_acknowledge(self):
        with patch('app.main.connection') as conn:
            r=self.client.post('/api/v1/alarmes/1/reconhecer',
                               json={'inquilino':'coop-cerrado'},headers=headers('leitor'))
            self.assertEqual(r.status_code,403);conn.assert_not_called()

    def test_gestor_creates_rule(self):
        with patch('app.main.connection') as factory:
            cm=MagicMock();factory.return_value.__enter__.return_value=cm
            cm.execute.return_value.fetchone.side_effect=[{'id':'sensor-1'}, None, {'id':7}]
            r=self.client.post('/api/v1/regras',json=RULE,headers=headers('gestor'))
            self.assertEqual(r.status_code,201)
            self.assertEqual(r.json()['id'],7)

    def test_operador_acknowledges_alarm(self):
        with patch('app.main.connection') as factory:
            cm=MagicMock();factory.return_value.__enter__.return_value=cm
            cm.execute.return_value.fetchone.return_value={'status':'ativo'}
            r=self.client.post('/api/v1/alarmes/17/reconhecer',
                json={'inquilino':'coop-cerrado'},headers=headers('operador'))
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json()['status'],'reconhecido')

    def test_rule_rejects_invalid_operator(self):
        bad={**RULE,'operador':'igual'}
        r=self.client.post('/api/v1/regras',json=bad,headers=headers('gestor'))
        self.assertEqual(r.status_code,422)

if __name__=='__main__':unittest.main()
