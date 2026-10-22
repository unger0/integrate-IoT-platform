# Plataforma IoT Integrada — Arch Linux (kit de laboratório)

**Ambiente principal:** notebook com Arch Linux; serviços em Docker Engine e Docker Compose; scripts em Bash/Python; frontend React opcional. 

**Referência:** Documento de Requisitos — Plataforma IoT Integrada, UniEVANGÉLICA, v2.0 (19/10/2026).

> **NÃO é o MVP completo nem uma implantação de produção.** Senhas fixas de demonstração, broker MQTT anônimo, API HTTP sem autenticação e fila SQLite não criptografada. Executar exclusivamente em localhost, com dados sintéticos.

## Início rápido — Arch Linux

Leia **[docs/05-arch-linux.md](docs/05-arch-linux.md)** para instalar e preparar Docker no Arch, incluindo riscos de permissões do grupo `docker`.

Depois de extrair o ZIP e entrar nesta pasta:

```bash
./scripts/linux/00-verificar-ambiente.sh
./scripts/linux/01-iniciar-laboratorio.sh
./scripts/linux/02-demonstrar-fluxo.sh
./scripts/linux/03-teste-desconexao.sh    # opcional: interrompe/restaura só a API
./scripts/linux/04-encerrar-laboratorio.sh
```

Para MQTT experimental, use `./scripts/linux/05-demo-mqtt.sh`. Para frontend React: `cd apps/web && npm install && npm run dev`.

**Documentos:** [migração/portabilidade](docs/06-portabilidade-e-migracao.md) · [arquitetura](docs/01-arquitetura.md) · [roteiro](docs/02-roadmap-e-backlog.md) · [testes](docs/03-plano-de-testes.md) · [matriz de requisitos](docs/matriz-rastreabilidade.csv).

**Portabilidade:** não foi necessário reescrever os serviços. O ambiente também pode funcionar em outras distribuições Linux e no Windows com a adaptação das instruções, mas o alvo desta entrega é Arch Linux.

## Objetivo e limites do documento

Construir uma **plataforma de integração IoT, neutra quanto ao cenário e à linguagem**, capaz de receber telemetria de um projeto urbano e de um rural, manter catálogo, perfis, locais, dispositivos, histórico, regras e alarmes, expor APIs e operar com nó de borda por 72 horas sem conectividade, com sincronização sem perdas/duplicações. O documento traz **69 RFs e 18 RNFs**: **33 Essenciais**, 30 Importantes e 6 Desejáveis. O MVP da fase 1 abrange **todos os Essenciais**; o kit entrega só uma primeira fatia funcional, não sua totalidade.

## Organização

```text
Plataforma_IoT_Integrada_ArchLinux/
├── README.md                         instruções e limitações
├── docs/
│   ├── 00-interpretacao-da-atividade.md
│   ├── 01-arquitetura.md
│   ├── 02-roadmap-e-backlog.md
│   ├── 03-plano-de-testes.md
│   ├── 04-riscos-e-questoes.md
│   ├── matriz-rastreabilidade.csv    69 RF + 18 RNF
│   └── adr/0001-tecnologias.md
├── contracts/
│   ├── telemetria.v1.schema.json
│   ├── exemplo-rural.json
│   ├── exemplo-urbano.json
│   ├── openapi-starter.yaml
│   └── asyncapi-starter.yaml
├── infra/
│   ├── compose.lab.yml
│   └── mosquitto/mosquitto.conf
├── services/
│   ├── central/                      FastAPI + PostgreSQL, telemetria HTTP
│   ├── mqtt-bridge/                  tradutor MQTT -> HTTP (experimental)
│   └── edge/                         fila SQLite + reenvio (experimental)
├── apps/web/                         painel React+TypeScript simples
└── scripts/                          demonstração urbana, rural, MQTT, verificação e linux/
```

Além das pastas mostradas, `docs/05-arch-linux.md`, `docs/06-portabilidade-e-migracao.md` e `scripts/linux/` contêm as adaptações ao Arch.

Os exemplos foram elaborados para aprendizagem. O núcleo definitivo deve respeitar **contratos versionados, módulos desacoplados, segurança por inquilino e dispositivo, DLQ, barramento confiável, observabilidade e testes formais**.
