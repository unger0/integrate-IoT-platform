# Versão 0.6.0 — Estado estimado de dispositivos

## Objetivo

Adicionar observação da pontualidade das medições por dispositivo, usando o intervalo definido no perfil (RF-DIS-06, **atendimento parcial**). Não envia comandos nem modifica as tabelas existentes. Preserva o modo JWT demonstrativo da versão 0.5.1 e os endpoints anteriores.

## Como funciona

A API oferece `GET /api/v1/operacao/dispositivos?inquilino=coop-cerrado&limite=500`. Para cada dispositivo da organização, consulta o perfil e o horário mais recente registrado na tabela `last_state`. A comparação é feita com a hora atual em UTC:

- `em_dia`: o último registro foi medido há **até 2 vezes** o intervalo esperado.
- `atrasado`: a última medição é mais antiga que esse período.
- `sem_dados`: não existe medição registrada no dispositivo.
- `sem_perfil`: existem medições, mas não foi definido um intervalo de envio por perfil.
- `relogio_inconsistente`: medição está mais de 5 minutos no futuro (possível erro de relógio).

Por exemplo, um dispositivo com intervalo esperado de 3.600 segundos só será classificado como atrasado após mais de 7.200 segundos desde sua última medição. A tolerância é **uma escolha didática configurada no código**, e não está definida no PDF. A regra de pontualidade não é equivalente a confirmar a conexão física, nem à detecção de falhas MQTT/LoRaWAN. Dados históricos recebidos tardiamente não tornam o sensor atual.

**Observações:** São retornados no máximo 500 dispositivos por consulta. A contagem é apenas dessa amostra. O parâmetro `inquilino` é verificado pelo modo JWT de laboratório; modo aberto continua sem autenticação. Não conectar a equipamentos físicos nem usar dados reais.

## Implantação no Arch Linux

1. Faça uma cópia dos seus arquivos editados localmente (o ZIP incremental sobrescreve caminhos iguais).
2. Extraia o ZIP v0.6.0 para `~/Projetos/IoT/`.
3. Na pasta do projeto, execute `./scripts/linux/17-atualizar-v060.sh`. Ele faz backup PostgreSQL, recria os serviços preservando modo aberto/JWT e testa a atualização.
4. Abra o painel com `./scripts/linux/07-iniciar-painel.sh` (ou recarregue a aba se já estiver rodando).
5. Na navegação lateral, selecione **Operação** para ver o diagnóstico e atualize quando desejar.

O painel é React local e utiliza a mesma API autenticada da versão anterior. Se o token renovou, valide o novo no navegador. Nenhuma tabela foi criada ou removida nesta versão.

## Testes e critérios

- Testes unitários cobrindo intervalos horários, limites, dados ausentes, relógio futuro e fusos.
- Testes de API com token para a própria organização e recusa para outra organização.
- Script somente-leitura `16-validar-operacao.sh` consulta a API com o token em arquivo local (sem imprimi-lo).
- Testes de integração com PostgreSQL real e compilação total do React devem ser confirmados no seu notebook.

## Próximos requisitos

Monitoramento mais confiável de heartbeat e intervalo efetivo; métricas Prometheus e logs estruturados (RF-OBS-01/02); OIDC e MFA (RF-SEG-01); TLS e controle por dispositivo em MQTT (RF-SEG-04); testes de carga e 72 h offline (RNFs).
