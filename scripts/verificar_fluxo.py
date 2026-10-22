"""Verifica leituras sintéticas urbana/rural após demos, sem novos pacotes."""
import argparse
import json
import time
from urllib.request import urlopen
from urllib.error import URLError

parser = argparse.ArgumentParser()
parser.add_argument('--timeout', type=int, default=60)
args = parser.parse_args()
SERVIDOR='http://127.0.0.1:8000'
ESPERADO={
    'ar-centro-03': 'pm25',
    'solo-talhao07-02': 'umidade_solo',
}

def obter(url):
    with urlopen(url, timeout=4) as r:
        return json.load(r)

end=time.monotonic()+args.timeout
while True:
    try:
        faltando=[]
        for device, measure in ESPERADO.items():
            result=obter(f'{SERVIDOR}/api/v1/dispositivos/{device}/telemetria?limite=1000')
            if not any(item['measurement_name']==measure for item in result.get('dados', [])):
                faltando.append(f'{device}/{measure}')
        if not faltando:
            print('[OK] Medições rural e urbana encontradas no histórico central.')
            print('[OK] Fluxo de laboratório validado; os RNFs e requisitos do MVP ainda não foram homologados.')
            break
        print('Aguardando:', ', '.join(faltando))
    except (OSError, URLError, ValueError) as exc:
        print('Aguardando API:',exc)
    if time.monotonic() >= end:
        raise SystemExit('[ERRO] Leitura(s) não persistidas no tempo previsto. Consulte os logs de api e edge.')
    time.sleep(2)
