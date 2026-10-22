"""Inferência didática de pontualidade de sensores, sem comandos ou ações externas.
O resultado avalia a data da medição, não confirma conectividade de rede em tempo real.
"""
from datetime import datetime, timezone

TOLERANCIA_RELOGIO_SEGUNDOS = 300
MULTIPLICADOR_ATRASO = 2


def avaliar_pontualidade(ultima_medicao: datetime | None,
                         intervalo_esperado_segundos: int | None,
                         agora: datetime) -> dict:
    """Classifica em_dia, atrasado, sem_dados, sem_perfil ou relogio_inconsistente.

    Não trata dados atrasados como recentes apenas porque chegaram agora.
    O `agora` explícito torna a função determinística nos testes.
    """
    if agora.tzinfo is None or agora.utcoffset() is None:
        raise ValueError('agora deve incluir fuso horário')
    if ultima_medicao is None:
        return {'estado': 'sem_dados', 'idade_segundos': None,
                'tolerancia_segundos': intervalo_esperado_segundos * MULTIPLICADOR_ATRASO
                    if intervalo_esperado_segundos is not None and intervalo_esperado_segundos > 0 else None}
    if ultima_medicao.tzinfo is None or ultima_medicao.utcoffset() is None:
        raise ValueError('ultima_medicao deve incluir fuso horário')
    idade = (agora.astimezone(timezone.utc)-ultima_medicao.astimezone(timezone.utc)).total_seconds()
    idade = round(idade, 3)
    if idade < -TOLERANCIA_RELOGIO_SEGUNDOS:
        return {'estado': 'relogio_inconsistente', 'idade_segundos': idade,
                'tolerancia_segundos': None}
    if not intervalo_esperado_segundos or intervalo_esperado_segundos <= 0:
        return {'estado': 'sem_perfil', 'idade_segundos': idade,
                'tolerancia_segundos': None}
    tolerancia = intervalo_esperado_segundos * MULTIPLICADOR_ATRASO
    return {'estado': 'em_dia' if idade <= tolerancia else 'atrasado',
            'idade_segundos': idade, 'tolerancia_segundos': tolerancia}
