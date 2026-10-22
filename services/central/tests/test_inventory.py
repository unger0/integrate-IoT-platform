"""Consulta de inventário por organização: testes isolados, sem banco real.
ATENÇÃO: filtro tenant_id não é autorização; RF-SEG-03 continua pendente.
"""
import unittest
from unittest.mock import MagicMock, patch
from app.main import list_devices, list_domains


class InventoryTests(unittest.TestCase):
    @patch('app.main.connection')
    def test_domains_use_tenant_parameter(self, factory):
        conn = MagicMock()
        factory.return_value.__enter__.return_value = conn
        conn.execute.return_value.fetchall.return_value = [{'name': 'agricultura'}, {'name': 'clima'}]
        out = list_domains('coop-cerrado')
        self.assertEqual(out['dominios'], ['agricultura', 'clima'])
        sql, parameters = conn.execute.call_args.args
        self.assertIn('tenant_id=%s', sql)
        self.assertEqual(parameters, ('coop-cerrado',))

    @patch('app.main.connection')
    def test_devices_use_tenant_and_limit(self, factory):
        conn = MagicMock()
        factory.return_value.__enter__.return_value = conn
        conn.execute.return_value.fetchall.return_value = [
            {'id':'soil-1','tenant_id':'coop-cerrado','domain':'agricultura',
             'site':'fazenda','area':None,'profile_name':None,'manufacturer':None,'firmware':None}
        ]
        out = list_devices('coop-cerrado', 75)
        self.assertEqual(out['total_retorno'], 1)
        self.assertEqual(out['dispositivos'][0]['id'], 'soil-1')
        sql, parameters = conn.execute.call_args.args
        self.assertIn('tenant_id=%s', sql)
        self.assertIn('LIMIT %s', sql)
        self.assertEqual(parameters, ('coop-cerrado', 75))


if __name__ == '__main__':
    unittest.main()
