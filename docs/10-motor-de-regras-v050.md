# Plataforma IoT — v0.5.0: regras de limite e alarmes

**Escopo:** evolução incremental do laboratório v0.4.0. Dados **sintéticos**. Não opera dispositivos reais.

## O que mudou

- Criação de regras simples por **organização + dispositivo + grandeza + unidade**.
- Operadores `maior_que` e `menor_que`, limites estritos e severidade configurável.
- Geração de alarmes na mesma transação que persiste a telemetria HTTP.
- Ciclo de vida: `ativo` → `reconhecido` → `resolvido` (resolução manual ou automática com nova medição normal).
- Um único alarme em aberto por par regra/dispositivo, mesmo após novas violações; as ocorrências são incrementadas.
- Registro de eventos de reconhecimento e resolução em `alarm_events`.
- Mensagens duplicadas não disparam novos alarmes; medições atrasadas são armazenadas no histórico, **mas não interferem no alarme atual**.
- Painel React com seção **Regras e alarmes** e contagem na visão geral.
- Novas tabelas `threshold_rules`, `alarms` e `alarm_events` adicionadas por comandos `CREATE TABLE IF NOT EXISTS`; volumes e dados anteriores preservados.

## APIs

| Método | Rota | Papel permitido no modo JWT didático |
|---|---|---|
| POST | `/api/v1/regras` | administrador, gestor |
| GET | `/api/v1/regras?inquilino=coop-cerrado` | administrador, gestor, operador, integrador, leitor |
| GET | `/api/v1/alarmes?inquilino=coop-cerrado` | administrador, gestor, operador, integrador, leitor |
| POST | `/api/v1/alarmes/{id}/reconhecer` | administrador, gestor, operador |
| POST | `/api/v1/alarmes/{id}/resolver` | administrador, gestor, operador |

Em todos os endpoints, a API verifica a organização do token JWT **apenas no modo protegido demonstrativo**. O modo aberto anterior continua sem segurança de produção.

Exemplo de regra:

```json
{
  "inquilino": "coop-cerrado",
  "nome": "solo-umido-alerta",
  "dispositivo": "solo-talhao07-02",
  "grandeza": "umidade_solo",
  "unidade": "%",
  "operador": "maior_que",
  "limite": 80,
  "severidade": "alta"
}
```

Uma leitura de 92% emite alarme; uma nova leitura de 42%, mais recente, resolve-o automaticamente. Isso é diferente da **classificação do perfil**: 92% pode estar dentro da faixa 0–100% do sensor (`conforme`), mas violar a condição de alerta (>80%).

## Instalar a atualização sem perder dados

1. Baixe `IoT_ArchLinux_atualizacao_v0.5.0.zip` em `~/Downloads`.
2. Extraia na **pasta-pai** do projeto:

```bash
unzip -o ~/Downloads/IoT_ArchLinux_atualizacao_v0.5.0.zip -d ~/Projetos/IoT/
cd ~/Projetos/IoT/Plataforma_IoT_Integrada_ArchLinux
```

3. Execute o script de atualização, que cria um `pg_dump`, detecta o modo vigente (aberto ou JWT) e recria os contêineres corretos **sem excluir volumes**:

```bash
./scripts/linux/13-atualizar-v050.sh
```

Se a API antiga não estava em execução, o script recusa atualizar para evitar alternar acidentalmente o modo de segurança. Nesse caso, inicie primeiro o modo correto com o script `01` (aberto) ou `09` (JWT demonstrativo).

**Modo JWT demonstrativo:** o script 09 renova os tokens. Você terá de copiar o novo token de `runtime/token-gestor.txt` para o campo do painel. Nunca compartilhe esse arquivo ou a chave `.env.protegido`.

4. Para demonstrar os alarmes sem usar Swagger manualmente:

```bash
./scripts/linux/12-demonstrar-alarmes.sh
```

5. Atualize o painel React em `http://127.0.0.1:5173` (se necessário, reinicie `./scripts/linux/07-iniciar-painel.sh`). Use a aba **Regras e alarmes**. O script de demonstração deixa um alarme **resolvido** no histórico; selecione o filtro **Todos**.

## Limites e exigências ainda não atendidas

- **RF-PRO-02 parcial:** só regra de limiar por dispositivo; ausência de dados, janela temporal, geografia e regra local na borda ainda pendentes.
- **RF-PRO-03 parcial:** a ação atualmente só cria alarme persistente; **não envia SMS, webhook, comandos, MQTT nem notificações**.
- **RF-PRO-05 parcial:** ciclo básico e severidade presentes, sem testes de resiliência, borda offline e SLA de produção.
- Leitura com unidade diferente da regra não a dispara; não implementamos conversão UCUM.
- Regras novas não são avaliadas retroativamente; execução síncrona simplificada, não há motor assíncrono nem fila de regras.
- A persistência HTTP ainda não garante durabilidade fim a fim do caminho MQTT nem é homologada a 1.000 mensagens/s.
- A geração de alarme na central **não equivale** a regras locais de irrigação: não conecte atuadores reais.
- A v0.4 acrescentou tokens demonstrativos; ainda faltam OIDC, MFA, autenticação MQTT/TLS, isolamento de produção e auditoria completa.

## Testes

No Docker, os testes antigos continuam disponíveis. A versão v0.5 acrescenta testes para operadores, limite estrito, leituras atrasadas, schemas e permissões de API; a demonstração `12` usa o PostgreSQL real **do notebook**. O código-fonte foi verificado sintaticamente no ambiente de preparação, mas a compilação React com as dependências npm não pôde ser realizada aqui. Isso deve ser verificado ao iniciar Vite no Arch Linux.
