# Plataforma IoT Integrada — versão 0.7.0
## Observabilidade básica: métricas, logs e resumo por organização

**Escopo:** incremento didático de RF-OBS-01 e RF-OBS-02 (atendimento parcial). A implementação **não** comprova as metas não funcionais, nem substitui OpenTelemetry, Prometheus Server, Grafana, Loki ou auditoria imutável.

### 1. Objetivos e conceitos

- **Métrica:** medição numérica agregada, como total de requisições HTTP ou duração de uma operação.
- **Contador (Counter):** somente cresce, podendo reiniciar com o processo.
- **Histograma (Histogram):** registra a distribuição de durações em grupos (*buckets*), permitindo obter proporções e percentis em um sistema de monitoramento.
- **Log estruturado:** evento em formato JSON, com campos fixos, facilitando consultas e identificação de falhas.
- **ID de correlação:** UUID que identifica uma requisição e permite relacioná-la com outros registros de um fluxo.

### 2. API e segurança

| Recurso | Uso | Controle |
|---|---|---|
| `GET /api/v1/observabilidade/resumo?inquilino=coop-cerrado` | Totais históricos de mensagens persistidas, classificações e alarmes abertos da organização | O mesmo filtro/validação por inquilino das outras APIs; leitura permitida para gestores e leitores |
| `GET /metrics` | Exportação de métricas HTTP e ingestão no formato Prometheus | No modo JWT: **somente papel administrador**. No modo aberto: acessível localmente, sem autenticação |
| `docker compose ... logs api` | Log de requisições e ingestão em JSON | Acesso ao Docker no notebook |
| `docker compose ... logs edge` | Log de fila e sincronizações em JSON | Acesso ao Docker no notebook |

**Atenção:** o resumo usa o PostgreSQL e possui números persistentes por organização, não expõe contadores HTTP globais. O endpoint `/metrics` possui contadores em memória de toda a API; por isso foi restrito a administrador no modo protegido. Ele não é apresentado ao gestor no painel. `POST /ingestao/lote` registra resultado por mensagem; um lote inteiramente inválido antes da validação do body gera contagem de rejeição da requisição e não de todas as mensagens desconhecidas.

As métricas atuais são:

- `iot_http_requests_total{method,route,status}`
- `iot_http_request_duration_seconds{method,route}` (série de histograma)
- `iot_telemetry_messages_total{channel,result}` com `channel = http|lote` e `result = aceita|duplicada|recusada`

Para evitar explosão de cardinalidade, **não existem rótulos com IDs de dispositivo, IDs de mensagem, tokens, tenants ou endereços IP**. A rota registrada é um template (`.../{id}`) ou `unmatched`, nunca um caminho de usuário sem normalização.

### 3. Correlação e limites

O backend devolve um cabeçalho `X-Correlation-ID` em respostas HTTP, gerando um UUID novo quando o cliente não envia um UUID válido. Os logs da API incluem esse ID e, nos eventos de ingestão, também o ID da mensagem, sem o conteúdo bruto da telemetria. Na sincronização, a borda encaminha `X-Correlation-ID` e registra os IDs das mensagens confirmadas.

O mecanismo é **correlação de logs básica**, não tracing distribuído padronizado. Logs de transporte ou middleware de terceiros podem ter formato diferente. Logs não possuem armazenamento persistente configurado fora do padrão do Docker. Contadores e histogramas reiniciam quando o processo central reinicia, e não há agregação entre réplicas.

### 4. Atualizar no Arch Linux

Da pasta que contém o projeto:

```bash
unzip -o ~/Downloads/IoT_ArchLinux_atualizacao_v0.7.0.zip -d ~/Projetos/IoT/
cd ~/Projetos/IoT/Plataforma_IoT_Integrada_ArchLinux
./scripts/linux/19-atualizar-v070.sh
```

O script cria **um novo backup PostgreSQL**, reconstrói os serviços no modo atual (aberto/JWT), executa a suíte Python e verifica o endpoint. Não apaga volumes. Se estiver em modo JWT, renova o token demonstrativo do gestor: cole-o apenas na interface local. Abra ou atualize o painel (`./scripts/linux/07-iniciar-painel.sh`) e selecione **Observabilidade**.

Para repetir apenas a verificação segura, sem modificar cadastros ou medições:

```bash
./scripts/linux/18-validar-observabilidade.sh
```

Para observar os logs:

```bash
docker compose -f infra/compose.lab.yml logs --tail=30 api
docker compose -f infra/compose.lab.yml logs --tail=30 edge
```

Evite incluir logs completos contendo dados pessoais em trabalhos entregues. **Não compartilhe** o conteúdo de `.env.protegido` ou `runtime/token-gestor.txt`.

### 5. Limitações e próximos passos

1. Implementação apenas local, sem OIDC, MFA, TLS, controle MQTT por dispositivo ou autenticação segura da borda.
2. Não há servidor Prometheus coletando e persistindo métricas, nem Grafana, Alertmanager, Loki ou OpenTelemetry.
3. Os contadores HTTP são globais à instância central; o resumo do painel é por organização e derivado dos dados persistidos. Valores de múltiplas réplicas não estão agregados.
4. Falta comprovar metas de **1.000 mensagens/s** e **p95 de persistência ≤ 2 s**, além do ciclo offline de 72 horas, backup/restauração real e isolamento completo.
5. A instrumentação não deve ser interpretada como auditoria permanente ou segurança de produção.

**Critério didático desta versão:** o usuário gestor consegue consultar os históricos de sua organização; não acessa `/metrics` no modo JWT. Um administrador com token temporário consegue obter métricas Prometheus; a API gera logs JSON com correlação. Verificar em ambiente Docker real antes de considerar aprovado.
