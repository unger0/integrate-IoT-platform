# Roteiro executável sugerido

O documento define três **fases de produto** (MVP, Integração e Evolução). A divisão abaixo em **incrementos de trabalho** é uma recomendação para ajudar no desenvolvimento e avaliação contínua; ela não muda a prioridade oficial de nenhum requisito.

## Incremento 0 — Fundação e entendimento

- Versionar repositório Git e combinar papéis do grupo.
- Documentar o problema, casos UC-01/UC-03/UC-06 e arquitetura.
- Publicar contratos JSON Schema, AsyncAPI e OpenAPI.
- Criar matriz com os 87 requisitos e critérios de aceite.
- Decidir ambiente local, gestão de segredos, formato de logs e testes.
- **Pronto quando:** contrato e estrutura aprovados, requisitos rastreáveis.

## Incremento 1 — Caminho mínimo de dados (laboratório, entregue parcialmente aqui)

- Banco central, API HTTP e lote.
- Dispositivo rural e urbano cadastrados.
- Validação da telemetria, deduplicação e ordenação por `timestamp`.
- Histórico e último estado coerentes.
- **Pronto quando:** scripts de demonstração enviam e consultam duas origens.
- **Ainda falta** concluir comportamentos de produção exigidos nos RFs de ingestão, incluindo DLQ e requisitos de desempenho.

## Incremento 2 — Segurança e catálogo completos (essenciais)

- Tenant/site/área/domínio/perfil por configuração; validação de grandezas e faixas.
- Keycloak ou outro OIDC, segundo fator para admins e RBAC.
- Token/certificado por dispositivo; revogação e ACL por tópico MQTT.
- Isolamento de inquilinos verificado por testes negativos e criptografia de dados/segredos.
- **Pronto quando:** um gestor cria um domínio novo sem mudança de código, e tentativas de leitura/publicação indevida são recusadas.

## Incremento 3 — Borda confiável (essenciais)

- Broker/HTTP local, fila cifrada, robustez sob energia instável.
- Store-and-forward, lote com ACK seguro e idempotência.
- Sincronização automática, preservando a hora original das medições.
- **Pronto quando:** teste de 72 h em ambiente de homologação passa sem perda/duplicação; fila retoma após queda do processo/energia.

## Incremento 4 — Regras, alarmes e observabilidade (essenciais)

- Normalização e enriquecimento; motor condição -> ação.
- Alarmes: ativo, reconhecido, resolvido; origem e timestamps corretos.
- API aberta versionada e paginação consistente.
- Logs JSON com id de correlação e métricas Prometheus.
- **Pronto quando:** regra de silo e histórico de alarmes são comprovados; métricas e logs permitem rastreamento.

## Incremento 5 — Homologação do MVP

- Integração de dois projetos (rural com borda e urbano direto).
- Integração em 3 linguagens sem SDK proprietário obrigatório.
- Testes de 1.000 mensagens/s, p95 de persistência <= 2 s, regras <= 3 s.
- Testar backups, recuperação, privacidade, disponibilidade, acessibilidade e cobertura.
- **Pronto quando:** critérios da seção 9.3 e todos os RFs Essenciais/RNFs cabíveis têm evidência.

## Fases posteriores (conforme documento)

- **Fase 2:** suporte espacial, conectores/LoRaWAN/NGSI-LD, comandos/gêmeo, SMS, dashboards configuráveis, agregações e sandbox. **Verificar conflito RF-INT-03**, classificado Essencial na própria tabela.
- **Fase 3:** CoAP, OTA canário, templates urbanos/rurais, painel offline local, mapeamento sem código e extensões de processamento.

## Organização sugerida de tarefas

Criar cartões por `RF-ID`, ligados a um teste de aceite e à evidência (log, relatório ou captura). Campos: ID, descrição do PDF, prioridade original, pessoa responsável, dependências, etapa proposta, status, teste, evidência. Não marcar um requisito como pronto só porque sua rota ou tela existe: validar **o critério integral**.
