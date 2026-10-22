"""Testes do motor de limiar sem dependência de banco de dados."""
import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from pydantic import ValidationError
from app.threshold_rules import violated, can_evaluate
from app.schemas import RegraLimiar, AcaoAlarme


def sample(**kwargs):
    data=dict(inquilino='coop-cerrado',nome='solo-critico',dispositivo='solo-talhao07-02',
              grandeza='umidade_solo',unidade='%',operador='maior_que',limite=80,severidade='alta')
    data.update(kwargs)
    return data

class RegraDeLimiteTests(unittest.TestCase):
    def test_above(self): self.assertTrue(violated(81,'maior_que',80))
    def test_not_above(self): self.assertFalse(violated(79,'maior_que',80))
    def test_boundary_above(self): self.assertFalse(violated(80,'maior_que',80))
    def test_below(self): self.assertTrue(violated(9,'menor_que',10))
    def test_not_below(self): self.assertFalse(violated(11,'menor_que',10))
    def test_boundary_below(self): self.assertFalse(violated(10,'menor_que',10))
    def test_bad_operator(self):
        with self.assertRaises(ValueError): violated(1,'maior_igual',1)
    def test_infinite(self):
        with self.assertRaises(ValueError): violated(float('inf'),'maior_que',1)
    def test_nan(self):
        with self.assertRaises(ValueError): violated(float('nan'),'maior_que',1)
    def test_old_measurement(self):
        now=datetime.now(timezone.utc)
        self.assertFalse(can_evaluate(now-timedelta(seconds=1),now))
    def test_repeated_time(self):
        now=datetime.now(timezone.utc)
        self.assertFalse(can_evaluate(now,now))
    def test_new_measurement(self):
        now=datetime.now(timezone.utc)
        self.assertTrue(can_evaluate(now+timedelta(seconds=1),now))
    def test_no_last_state(self):
        self.assertTrue(can_evaluate(datetime.now(timezone.utc),None))
    def test_schema_valid(self):
        self.assertEqual(RegraLimiar(**sample()).operador,'maior_que')
    def test_schema_bad_unit(self):
        with self.assertRaises(ValidationError): RegraLimiar(**sample(unidade=''))
    def test_schema_bad_operator(self):
        with self.assertRaises(ValidationError): RegraLimiar(**sample(operador='igual'))
    def test_schema_bad_limit(self):
        with self.assertRaises(ValidationError): RegraLimiar(**sample(limite=float('inf')))
    def test_schema_bad_severity(self):
        with self.assertRaises(ValidationError): RegraLimiar(**sample(severidade='extrema'))
    def test_action_body_tenant(self):
        self.assertEqual(AcaoAlarme(inquilino='coop-cerrado').inquilino,'coop-cerrado')

if __name__ == '__main__': unittest.main()
