# Alertas, dependências e questões de escopo

1. **RF-INT-03 é Essencial**, mas o roteiro da seção 9.2 inclui adaptadores plugáveis na Fase 2. Por segurança de rastreabilidade, planejar o RF para o MVP e pedir definição explícita de escopo.
2. **RF-PRO-03 é Essencial** e exige demonstrar alarme, notificação, comando, webhook e publicação em tópico. Alguns canais específicos aparecem como Importantes (RF-APP-03/05, RF-DIS-05). Separar o motor de ações dos conectores concretos e esclarecer o teste mínimo aceito.
3. **RF-PRO-02** inclui condições com área geográfica, ao passo que geometrias/consultas espaciais são RF-CEN-04 Importante. Definir como avaliar a capacidade mínima no MVP.
4. O roteiro solicita **painel básico no MVP**, mas RF-APP-04/06 (painel configurável/interface responsiva) têm prioridade Importante. Documentar uma interface simples inicial e a evolução.
5. O documento requer **MQTT 3.1.1 e 5.0 sobre TLS, autorização por tópico e ACK sem perda**: um broker anônimo e uma ponte que usa HTTP após PUBACK são apenas protótipo; não cumprem confiabilidade fim a fim.
6. **Borda**: persistência SQLite por si só não satisfaz a exigência de fila cifrada, credencial por nó, 72 horas e funcionamento com queda de energia. É necessária engenharia específica e ensaio prolongado.
7. **Escalabilidade/latência**: prova com 1.000 msg/s não se deduz de código; exige medição com hardware, carga e percentis.
8. **LGPD**: minimizar dados pessoais, definir acesso, retenção, transparência e trilhas conforme a aplicação; dados GPS/placas podem ser pessoais.
9. **Interface aberta**: preservar JSON Schema, OpenAPI, AsyncAPI, UCUM e GeoJSON; nunca amarrar o integrador a uma biblioteca proprietária.
10. **Separação contratual**: o kit inclui contratos iniciais ilustrativos e um subconjunto de rotas; versões definitivas têm de ser completadas antes de homologação.

## Perguntas úteis para a orientação

- Qual prazo, tamanho da equipe e infraestrutura de homologação estão disponíveis?
- Os 33 RFs Essenciais e todas as métricas RNF deverão estar **implementados** ou parte pode ser apresentada como proposta arquitetural?
- Os critérios dos RF-PRO-03, RF-PRO-02, RF-INT-03 e painel básico permanecem tais como escritos, mesmo havendo dependências inter-fases?
- Os sensores devem ser físicos ou simulados são aceitos nos casos de uso?

Até a orientação, não omitir requisitos em silêncio: classificá-los como **pendentes** e registrar explicitamente que a entrega do kit é apenas a fundação.
