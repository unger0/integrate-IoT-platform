"""Testes unitários independentes de banco de dados (laboratório)."""
import unittest
from pydantic import ValidationError
from app.schemas import Medida, NovoPerfil
from app.profile_rules import avaliar_medida

REGRA = {'umidade_solo': {'unidade': '%', 'minimo': 0.0, 'maximo': 100.0}}

class PerfilTestes(unittest.TestCase):
    def test_conforme(self):
        self.assertEqual(avaliar_medida(Medida(grandeza='umidade_solo', valor=23.5, unidade='%'), REGRA),
                         ('conforme', None))

    def test_limites_inclusivos(self):
        for valor in (0, 100):
            self.assertEqual(avaliar_medida(Medida(grandeza='umidade_solo', valor=valor, unidade='%'), REGRA),
                             ('conforme', None))

    def test_valor_suspeito(self):
        self.assertEqual(avaliar_medida(Medida(grandeza='umidade_solo', valor=125, unidade='%'), REGRA),
                         ('suspeita', 'valor_fora_da_faixa'))

    def test_unidade_incompativel(self):
        self.assertEqual(avaliar_medida(Medida(grandeza='umidade_solo', valor=30, unidade='Cel'), REGRA),
                         ('suspeita', 'unidade_incompativel'))

    def test_grandeza_desconhecida(self):
        self.assertEqual(avaliar_medida(Medida(grandeza='pressao', valor=5, unidade='Pa'), REGRA),
                         ('suspeita', 'grandeza_nao_prevista'))

    def test_sem_perfil(self):
        self.assertEqual(avaliar_medida(Medida(grandeza='umidade_solo', valor=23.5, unidade='%'), None),
                         ('nao_avaliada', None))

    def test_faixa_invalida_recusada(self):
        with self.assertRaises(ValidationError):
            NovoPerfil(inquilino='x',nome='p',dominio='d',intervalo_esperado_segundos=60,
                       medidas=[{'grandeza':'t','unidade':'Cel','minimo':50,'maximo':20}])

    def test_grandezas_duplicadas_recusadas(self):
        with self.assertRaises(ValidationError):
            NovoPerfil(inquilino='x',nome='p',dominio='d',intervalo_esperado_segundos=60,
                       medidas=[{'grandeza':'t','unidade':'Cel','minimo':0,'maximo':30},
                                {'grandeza':'t','unidade':'Cel','minimo':0,'maximo':50}])

    def test_intervalo_invalido_recusado(self):
        with self.assertRaises(ValidationError):
            NovoPerfil(inquilino='x',nome='p',dominio='d',intervalo_esperado_segundos=0,
                       medidas=[{'grandeza':'t','unidade':'Cel','minimo':0,'maximo':50}])

    def test_valor_nao_finito_recusado(self):
        with self.assertRaises(ValidationError):
            Medida(grandeza='umidade_solo', valor=float('nan'), unidade='%')

if __name__ == '__main__':
    unittest.main()
