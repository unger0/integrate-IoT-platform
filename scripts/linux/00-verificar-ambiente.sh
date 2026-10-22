#!/usr/bin/env bash
# Verifica dependências; não instala nada nem modifica o sistema.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
echo '== Plataforma IoT | verificação de ambiente =='
if [[ -r /etc/os-release ]]; then
  source /etc/os-release
  echo "Sistema: ${PRETTY_NAME:-Linux}";
  if [[ "${ID:-}" != 'arch' && " ${ID_LIKE:-} " != *' arch '* ]]; then
    echo '[AVISO] O guia foi escrito para Arch Linux; confira os comandos da sua distribuição.'
  fi
fi
printf 'Kernel: '; uname -r
printf 'Arquitetura: '; uname -m
if command -v docker >/dev/null 2>&1; then
  docker --version
  if docker compose version >/dev/null 2>&1; then
    docker compose version
  else
    echo '[ERRO] docker compose não encontrado. No Arch, instale docker-compose.'
  fi
  if docker info >/dev/null 2>&1; then
    echo '[OK] Docker daemon acessível a este usuário.'
  else
    echo '[ERRO] Docker daemon inacessível neste terminal.'
    echo '       Verifique: sudo systemctl enable --now docker.service'
    echo '       Para usar sem sudo, consulte as opções e riscos no guia docs/05-arch-linux.md.'
  fi
else
  echo '[ERRO] Docker não encontrado. Instale docker, docker-compose e docker-buildx.'
fi
for cmd in python node npm curl; do
  if command -v "$cmd" >/dev/null 2>&1; then
    case "$cmd" in
      python) echo "Python: $(python --version 2>&1)";;
      node) echo "Node: $(node --version)";;
      npm) echo "npm: $(npm --version)";;
      curl) echo "curl: disponível";;
    esac
  else
    if [[ "$cmd" == node || "$cmd" == npm ]]; then echo "[OPCIONAL] $cmd ausente (usado no frontend).";
    else echo "[AVISO] $cmd ausente."; fi
  fi
done
echo "Pasta: $ROOT"
echo 'Leitura recomendada: docs/05-arch-linux.md'
