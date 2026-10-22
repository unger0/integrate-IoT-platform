# Versão 0.2.0 — Perfis de dispositivos (RF-CEN-02, implementação inicial)

## Finalidade

Um perfil descreve **quais grandezas** o dispositivo mede, a **unidade exata** de cada uma, a **faixa** mínima/máxima permitida e o **intervalo esperado** entre transmissões. O catálogo é definido por organização (*inquilino*) e não possui tipos rurais ou urbanos fixos.

**Importante:** `intervalo_esperado_segundos` é persistido, mas ainda não dirige um monitor online/offline. RF-DIS-06 permanece pendente. Não há validação completa do modelo GeoJSON, autenticação, segurança por inquilino, normalização UCUM, DLQ ou controle de acesso. Esses dados são de laboratório.

## Mudanças no banco de dados

No startup, a API cria as tabelas `device_profiles` e `profile_measures`, e **acrescenta** (sem remover dados) colunas nas tabelas `devices`, `measurements` e `last_state`. A migração é **aditiva e repetível**, mas ainda provisória; o projeto definitivo deverá usar Alembic, rollback planejado e testes de evolução do esquema.

Históricos anteriores passam a ter `quality = nao_avaliada`. Mesmo vinculando um perfil a um sensor existente, medições anteriores não são reclassificadas automaticamente.

## Campos de classificação

- `quality = conforme`: grandeza prevista, unidade igual e valor dentro da faixa (limites inclusivos).
- `quality = suspeita`: grandeza não prevista, unidade incompatível ou valor fora da faixa.
- `quality = nao_avaliada`: dispositivo sem perfil vinculado, ou medição de versão anterior.
- `quality_reason`: um dos motivos `grandeza_nao_prevista`, `unidade_incompativel` ou `valor_fora_da_faixa`; caso contrário, `null`.

**Leituras suspeitas são armazenadas** com sua classificação; não são automaticamente descartadas e não criam alarmes nesta versão.

## Novas operações

| Operação | Objetivo |
|---|---|
| `POST /api/v1/catalogo/perfis` | Criar perfil e grandezas por inquilino |
| `GET /api/v1/catalogo/perfis?inquilino=...` | Listar perfis |
| `GET /api/v1/catalogo/perfis/{inquilino}/{nome}` | Inspecionar um perfil |
| `PUT /api/v1/dispositivos/{id}/perfil` | Vincular perfil a um dispositivo já cadastrado |

`POST /api/v1/dispositivos` também aceita os campos opcionais `perfil`, `fabricante` e `firmware`. Os campos antigos permanecem aceitos. `GET /api/v1/dispositivos/{id}/telemetria` e `/estado` acrescentam `quality` e `quality_reason`.

## Pré-requisitos e atualização segura de uma instalação existente

1. **Na pasta original do projeto, faça backup do banco** (com a API funcionando):

   ```bash
   mkdir -p backups
   docker compose -f infra/compose.lab.yml exec -T db pg_dump -U iot_lab -d iot_laboratorio > "backups/iot-antes-v020-$(date +%Y%m%d-%H%M%S).sql"
   ```

   Confira se o arquivo contém dados antes de alterar o projeto. O backup pode conter dados sensíveis: não o publique no Git.

2. Se usar um ZIP de atualização parcial, entre na pasta original e extraia-o na pasta `~/Projetos/IoT` (pai da pasta do projeto), mantendo as subpastas.
3. Recrie apenas os serviços alterados, **sem apagar volumes**:

   ```bash
   ./scripts/linux/01-iniciar-laboratorio.sh
   ```

4. Confira a versão `0.2.0` em `http://localhost:8000/docs`.
5. Execute os testes do fluxo antigo e os novos:

   ```bash
   ./scripts/linux/02-demonstrar-fluxo.sh
   ./scripts/linux/06-demonstrar-perfis.sh
   ```

**Não execute `docker compose down -v`** porque o comando remove volumes com as medições e o banco.

## Exemplo de perfil

```json
{
  "inquilino": "coop-cerrado",
  "nome": "solo-lab-v02",
  "dominio": "agricultura",
  "intervalo_esperado_segundos": 600,
  "medidas": [
    {"grandeza": "umidade_solo", "unidade": "%", "minimo": 0, "maximo": 100},
    {"grandeza": "temperatura_solo", "unidade": "Cel", "minimo": -10, "maximo": 65}
  ]
}
```

As faixas são **valores didáticos**, não especificações de sensores reais. Para mensagens com `umidade_solo` maior que 100%, a API grava `quality = suspeita` e `quality_reason = valor_fora_da_faixa`.

## Verificação

`06-demonstrar-perfis.sh` roda testes unitários Python e, em seguida, executa duas ingestões reais no backend: uma válida e outra fora da faixa. A confirmação da API é verificada por `message_id`, evitando falsos positivos causados por registros antigos. É um teste de laboratório; os requisitos não funcionais e as garantias de segurança continuam pendentes.
