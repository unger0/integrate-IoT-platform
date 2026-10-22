# ADR-0001 — Stack inicial e processo de evolução

- **Status:** proposta para protótipo, sujeita à equipe.
- **Contexto:** integrar urbano/rural, independência de linguagem, borda offline, contratos abertos e componentes de código aberto.
- **Decisão recomendada:** FastAPI/Python na API central e no protótipo da borda; React+TypeScript no frontend; PostgreSQL central; SQLite borda; Mosquitto MQTT; Docker Compose local. Em estágio posterior: PostgreSQL com TimescaleDB/PostGIS, broker protegido, barramento persistente, Keycloak/OIDC, métricas, logs estruturados e outros recursos conforme requisitos.
- **Justificativa:** facilita estudar contratos e validar rapidamente um fluxo completo, preservando separação por fronteiras e permitindo substituir componentes.
- **Trade-offs:** a abordagem inicial **não** entrega isolamento seguro, alta disponibilidade, throughput de 1.000 msg/s, criptografia, DLQ ou garantia de entrega MQTT. Exige refatoração antes do MVP final.
- **Alternativas do documento:** EMQX/Mosquitto, NATS/RabbitMQ/Kafka, Grafana, Node-RED, Orion-LD, ChirpStack. Não são imposições; o documento deixa a escolha aberta.
