"""Aguarda serviços HTTP do laboratório (biblioteca padrão)."""
import argparse
import time
from urllib.request import urlopen
from urllib.error import URLError

parser = argparse.ArgumentParser()
parser.add_argument('--timeout', type=int, default=60)
args = parser.parse_args()
if args.timeout <= 0:
    parser.error('--timeout deve ser positivo')

SERVICOS = {
    'API central': 'http://127.0.0.1:8000/health',
    'Nó de borda': 'http://127.0.0.1:8001/health',
}
end = time.monotonic() + args.timeout
for name, url in SERVICOS.items():
    while True:
        try:
            with urlopen(url, timeout=2) as r:
                if r.status == 200:
                    print(f'[OK] {name}: {url}')
                    break
        except (OSError, URLError):
            pass
        if time.monotonic() >= end:
            raise SystemExit(f'[ERRO] {name} não respondeu no limite de {args.timeout}s. Verifique os logs.')
        time.sleep(2)
