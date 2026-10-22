# Implantação do laboratório no Arch Linux

> Escopo: **laboratório local**, sem autenticação/TLS/segredos de produção. O documento original exige essas características no MVP completo. Não expor o broker MQTT, API ou PostgreSQL diretamente à internet.

## 1. O que realmente muda em relação ao Windows?

| Item | Windows (guia anterior) | Arch Linux (guia atual) |
|---|---|---|
| Gerência do Docker | Docker Desktop + WSL 2 | Docker Engine do repositório oficial + systemd (sem WSL) |
| Pacotes | Instaladores / winget | `pacman` |
| Terminal | PowerShell | bash ou zsh |
| Caminhos | `C:\...` / `\.venv\Scripts` | `~/...` / `.venv/bin` |
| Permissões do Docker | Docker Desktop | daemon e acesso ao socket Docker |
| Virtual environment | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| Dockerfile, API, PostgreSQL, MQTT, painel | Mesmo código | Mesmo código |

**Não é preciso reescrever os serviços**: a central, a borda e a ponte MQTT utilizam imagens Linux no Compose, enquanto os simuladores Python e o React são multiplataforma.

## 2. Pré-requisitos do notebook

- Arch Linux iniciado e conectado à internet, com acesso a `sudo`/`pacman`.
- Notebook preferencialmente x86_64, com espaço suficiente para imagens Docker; 8 GB de RAM ou mais é recomendação prática para laboratório, **não um requisito formal do PDF**.
- Docker Engine e Docker Compose; Python 3; Node.js/npm somente para interface web; `unzip` para extração.
- Um editor como VS Code ou outro editor, opcional.

Confirme a arquitetura com `uname -m` e o estado dos recursos com `free -h` e `df -h`.

## 3. Instalação via repositórios oficiais

No terminal Arch Linux:

```bash
sudo pacman -Syu --needed docker docker-compose docker-buildx python python-pip nodejs npm unzip git curl
```

- `sudo`: executa a instalação com privilégios administrativos.
- `pacman`: gerenciador oficial de pacotes do Arch.
- `-Syu`: sincroniza pacotes e atualiza o sistema (evita *partial upgrades*).
- `--needed`: evita reinstalações desnecessárias de pacotes atuais.
- `docker`: cliente e daemon do Docker Engine.
- `docker-compose`: plugin para `docker compose`.
- `docker-buildx`: construtor de imagens.

Se a atualização de pacotes instalar um kernel novo, reinicie o notebook conforme necessário antes de iniciar o Docker.

### 3.1 Ativar Docker com systemd

```bash
sudo systemctl enable --now docker.service
sudo systemctl status docker.service --no-pager
```

`systemctl` controla serviços gerenciados pelo systemd. `enable` configura a inicialização ao ligar; `--now` também inicia imediatamente. `status` mostra o estado. Se preferir não habilitar o Docker no boot, use somente `sudo systemctl start docker.service`.

### 3.2 Acesso ao daemon Docker (escolha UMA abordagem)

**Opção mais conservadora:** use `sudo docker ...` manualmente e execute os simuladores Python como seu usuário comum. Os scripts `scripts/linux/*.sh` foram preparados para o usuário com acesso direto ao Docker; não use `sudo` para executar todo o projeto por hábito.

**Opção prática para ambiente de desenvolvimento pessoal:** autorizar seu usuário a acessar Docker diretamente:

```bash
sudo usermod -aG docker "$USER"
```

Saia de sua sessão gráfica e entre novamente (ou execute `newgrp docker` no terminal) para a associação ao grupo entrar em vigor. Depois verifique:

```bash
docker info
docker compose version
```

**Alerta de segurança:** fazer parte do grupo `docker` equivale, na prática, a conceder poderes de administrador sobre o host. Faça isso somente se aceitar essa implicação. Alternativas mais restritivas incluem usar `sudo` para os comandos Docker ou configurar Docker em modo rootless (processo separado). Não execute `chmod 666 /var/run/docker.sock`.

### 3.3 Verificação da instalação

```bash
python --version
node --version
npm --version
docker --version
docker compose version
docker info
```

Se `docker info` falhar por permissão, verifique acesso ao daemon, não modifique permissões do socket indiscriminadamente.

## 4. Extração e primeiro uso

Se o ZIP estiver em `~/Downloads`:

```bash
mkdir -p ~/Projetos/IoT
unzip ~/Downloads/Plataforma_IoT_Integrada_ArchLinux.zip -d ~/Projetos/IoT
cd ~/Projetos/IoT/Plataforma_IoT_Integrada_ArchLinux
```

Se já estiver extraído em outro local, entre na pasta com `cd` e confira que `infra/compose.lab.yml` existe.

```bash
./scripts/linux/00-verificar-ambiente.sh
./scripts/linux/01-iniciar-laboratorio.sh
./scripts/linux/02-demonstrar-fluxo.sh
```

Os arquivos `.sh` possuem permissão de execução no ZIP. Se a extração não preservar permissões (ou se foram copiados por outro meio):

```bash
chmod +x scripts/linux/*.sh
```

**Serviços:** API `http://localhost:8000/docs`, saúde da borda `http://localhost:8001/health`, broker MQTT `127.0.0.1:1883`, banco PostgreSQL `127.0.0.1:5432`.

Também é possível executar sem scripts auxiliares:

```bash
docker compose -f infra/compose.lab.yml up --build -d
python scripts/aguardar_servicos.py
python scripts/demo_central.py
python scripts/demo_borda.py
python scripts/verificar_fluxo.py
```

## 5. Ensaiar a borda desconectada

```bash
./scripts/linux/03-teste-desconexao.sh
```

O script valida central e borda, cadastra dispositivos de laboratório, interrompe temporariamente **somente o contêiner `api`**, envia leitura à fila SQLite, recupera a API no bloco `finally`, espera sincronizar e verifica que as duas medidas do UUID enviado estão no histórico.

Esse script representa indisponibilidade temporária do **serviço central**, não um teste real de rede ou 72 horas, nem prova segurança/durabilidade do produto final. Evite executar testes paralelos no mesmo ambiente.

## 6. MQTT experimental

```bash
./scripts/linux/05-demo-mqtt.sh
```

O script cria `.venv` com `python -m venv`, instala `paho-mqtt` **dentro do ambiente virtual**, habilita o profile MQTT no Compose e publica uma leitura de teste. O Arch gerencia o Python do sistema com `pacman`; não utilize `sudo pip install` nem `pip install --break-system-packages` para fazer essa demonstração.

**Importante:** broker anônimo, sem TLS e ponte MQTT sem confirmação fim a fim. Somente loopback local em rede Docker do laboratório. Não vale como aceite de RF-ING-01/RNF-10.

### 6.1 Interface React (opcional)

```bash
cd apps/web
npm install
npm run dev
```

Abra `http://localhost:5173`. Para sair do servidor de desenvolvimento, use `Ctrl+C`. Para voltar à raiz: `cd ../..`.

## 7. Logs, diagnóstico e encerramento

```bash
docker compose -f infra/compose.lab.yml ps
docker compose -f infra/compose.lab.yml logs --tail 100 api
docker compose -f infra/compose.lab.yml logs --tail 100 edge
sudo systemctl status docker.service --no-pager
```

- `permission denied` no socket Docker: acesso ao daemon negado.
- `Cannot connect to the Docker daemon`: serviço parado, socket indisponível ou contexto incorreto.
- `Address already in use`: alguma porta (8000, 8001, 1883 ou 5432) já foi ocupada por outro processo.
- `ModuleNotFoundError` no demo MQTT: instale `paho-mqtt` no `.venv`.
- `externally-managed-environment`: você tentou instalar pacote Python globalmente; utilize `.venv`.
- Falha no build: confirme acesso à internet, `docker info`, `docker buildx version` e espaço livre (`df -h`).
- `404` na API: confira o endpoint e se o dispositivo já foi cadastrado.
- `connection refused` no frontend: central indisponível ou o endereço de API está incorreto.

Para encerrar preservando o banco:

```bash
./scripts/linux/04-encerrar-laboratorio.sh
```

**Não execute `docker compose ... down -v` sem intenção explícita de apagar os volumes**, especialmente o banco de dados e a fila SQLite.

## 8. O que ainda NÃO está entregue

A instalação no Arch **não altera o escopo funcional**. Ainda faltam os módulos e garantias essenciais do PDF: autenticação OIDC/MFA, autorização por papel e inquilino, credenciais e ACL de dispositivos, TLS, criptografia do nó de borda, mensageria durável, DLQ e tratamento sistemático de erros, validação completa de contratos, regras/ações e alarmes, métricas/logs estruturados, testes de carga, 72h offline e evidência de desempenho. Consulte `docs/02-roadmap-e-backlog.md` e `docs/03-plano-de-testes.md`.

## Referências de implantação (extras ao PDF)

- ArchWiki Docker: https://wiki.archlinux.org/title/Docker
- Pacotes oficiais Docker: https://archlinux.org/packages/extra/x86_64/docker/
- Pacotes oficiais Compose: https://archlinux.org/packages/extra/x86_64/docker-compose/
- ArchWiki Python/Virtual environment: https://wiki.archlinux.org/title/Python/Virtual_environment
