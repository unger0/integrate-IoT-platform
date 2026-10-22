"""Avaliação pura de regras de limiar do laboratório v0.5.0.

Não dispara dispositivos físicos nem faz notificações externas.
"""
from math import isfinite
from typing import Literal

Operator = Literal['maior_que', 'menor_que']


def violated(value: float, operator: Operator, limit: float) -> bool:
    """True se a condição de alarme está satisfeita (limites estritos)."""
    if not isfinite(value) or not isfinite(limit):
        raise ValueError('limiar e medição devem ser finitos')
    if operator == 'maior_que':
        return value > limit
    if operator == 'menor_que':
        return value < limit
    raise ValueError('operador desconhecido')


def can_evaluate(message_time, current_time) -> bool:
    """Ignora medições atrasadas e timestamps repetidos para alarmes atuais."""
    return current_time is None or message_time > current_time
