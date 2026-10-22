# O que a atividade efetivamente pede

Fonte: *Documento de Requisitos — Plataforma IoT Integrada*, UniEVANGÉLICA, versão 2.0, 19/10/2026.

## Problema

Projetos IoT diferentes têm protocolos, servidores, bancos e painéis isolados. A solução integra telemetria e informações, com **mesmo núcleo** para cidade e campo. O cenário é configuração, nunca uma divisão fixa no código.

## Entregas previstas no próprio documento

- **Fase 1 — MVP:** todos os requisitos marcados como Essencial, incluindo catálogo/domínios/perfis/locais, MQTT/HTTP/lotes, validação, deduplicação, dados atrasados, nó de borda e sincronização, cadastro/credenciais, regras/alarmes, séries históricas, último estado, API documentada, segurança multi-inquilino, métricas/logs. O resumo da fase prevê painel básico, embora o requisito de painéis configuráveis (RF-APP-04) seja Importante.
- **Fase 2 — Integração:** recursos Importantes, como LoRaWAN/NGSI-LD, gêmeo/comandos, integração API/webhook, geometrias/consultas espaciais, SMS, conectores e regras na borda.
- **Fase 3 — Evolução:** recursos Desejáveis, como CoAP, OTA, mapeamento simples sem código, modelos prontos e painel local do nó de borda.

**Verificar divergência:** RF-INT-03 (adaptadores plugáveis sem recompilação/reinício) aparece como **Essencial**, mas o quadro de roteiro localiza “adaptadores plugáveis” na Fase 2. A matriz preserva a prioridade individual (Essencial). Há dependência semelhante no RF-PRO-03 (ações como webhook/comando), embora integrações correspondentes apareçam como Importantes. Esclarecer a delimitação exata com o professor.

## Arquitetura exigida

Seis camadas: (1) dispositivos/borda; (2) conectividade/ingestão; (3) gestão; (4) processamento/regras; (5) dados; (6) aplicação/serviços, mais segurança, observabilidade e administração transversais. Serviços organizados segundo arquitetura hexagonal, contratos abertos e padrão de mensagem canônica.

## Provas finais de aceite que não podem faltar

1. Projeto urbano e projeto rural realmente integrados; rural usando borda.
2. Borda desconectada por **72 horas**, seguida de sincronização sem perda nem duplicação.
3. Domínio novo criado só por configuração (sem editar código do núcleo).
4. Integração demonstrada em **três linguagens** diferentes.
5. Ensaio de carga comprovando **RNF-01** (1.000 msg/s no MVP em servidor central) e **RNF-02** (p95 <= 2 s até persistir e <= 3 s para disparar regra).

## Não confundir a prova de conceito com a solução final

O laboratório anexado valida apenas uma primeira fatia: cadastro mínimo, HTTP, lote, persistência, último estado, leitura ordenada pelo timestamp, fila de borda, reenvio e interface ilustrativa. Ele NÃO implementa os 33 requisitos Essenciais nem atende os 18 RNFs. Use a matriz para acompanhar o que continua pendente.
