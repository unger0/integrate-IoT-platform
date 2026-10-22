"""Avaliação pura de qualidade: perfil configurável, sem dependência de banco.

Não rejeita automaticamente uma leitura física suspeita. Armazena com qualidade
'suspeita' para posterior investigação (requisito RF-CEN-02, estágio inicial).
"""
from .schemas import Medida


def avaliar_medida(medida: Medida, perfil: dict | None) -> tuple[str, str | None]:
    if perfil is None:
        return 'nao_avaliada', None
    regra = perfil.get(medida.grandeza)
    if regra is None:
        return 'suspeita', 'grandeza_nao_prevista'
    if medida.unidade != regra['unidade']:
        return 'suspeita', 'unidade_incompativel'
    if not regra['minimo'] <= medida.valor <= regra['maximo']:
        return 'suspeita', 'valor_fora_da_faixa'
    return 'conforme', None
