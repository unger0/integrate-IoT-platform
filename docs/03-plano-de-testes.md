# Plano de testes e evidências

## Cenários mínimos do MVP (seção 9.3)

| Caso | Procedimento | Evidência de aceite |
|---|---|---|
| T-01 Cidade e campo | Integrar uma estação urbana e um sensor rural passando por borda | Mensagens em histórico/API do inquilino correto |
| T-02 Desconexão 72 h | Cortar link central/borda; continuar medindo; restaurar | Quantidade e IDs batem exatamente; sem duplicatas; ordem pelo timestamp da medição |
| T-03 Novo domínio | Criar `recursos_hidricos` e perfil sem recompilar/reiniciar núcleo | Envio, API e painel disponíveis sem mudar código |
| T-04 Independência | Clientes MQTT/HTTP em três linguagens | Contratos iguais, sem SDK proprietário |
| T-05 Carga | Simular >= 1.000 msg/s em 1 servidor | Métricas de throughput e p95 persistência <= 2 s, disparo de regras <= 3 s |

## Outros testes essenciais de rastreabilidade

- RF-ING-03: enviar um lote com **5.000** mensagens, 3 inválidas; comprovar 4.997 persistidas e 3 erros individualizados.
- RF-ING-06: JSON fora do schema deve ir à **DLQ**, com motivo verificável.
- RF-ING-08: mesmo UUID reenviado deve ser gravado uma única vez.
- RF-ING-04: medição com 48h de atraso entra no histórico pelo timestamp original e não dispara alarme como atual.
- RF-SEG-01/02/03: MFA de administrador, RBAC e isolamento de dados entre inquilinos; testes negativos.
- RF-SEG-04/05: dispositivo não publica no tópico alheio; nó de borda tem credencial própria e fila cifrada.
- RF-DIS-06: sensor com período esperado de 1h não fica offline aos 5 minutos.
- RNF-04/07/10: janela offline, reinício abrupto, desligamento elétrico e recuperação sem perda de ACKs.
- RNF-11/12: TLS 1.2+, segredo e fila cifrados e tratamento de dados pessoais conforme LGPD.
- RNF-15/16: cobertura do núcleo >= 70%, análise estática sem falhas críticas, acessibilidade WCAG 2.1 AA.
- RNF-18: backup diário, RPO <= 24h, RTO <= 4h.

## Evidências recomendadas

Para cada teste: ID, versão de código, data, ambiente/hardware, conjunto de entrada, procedimento, resultado esperado, resultado obtido, logs/métricas, capturas e conclusão. Criar diretório `evidencias/` no momento da execução e não incluir credenciais nos relatórios.

**Importante:** os scripts `scripts/demo_*.py` são uma prova de fluxo didática. Eles não substituem os testes formais de aceite acima.
