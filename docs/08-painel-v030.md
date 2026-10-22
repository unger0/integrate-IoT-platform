# Versão 0.3.0 — Painel web de cadastro e monitoramento (LABORATÓRIO)

## Objetivo

Reduzir a dependência do Swagger para as demonstrações acadêmicas. Agora o painel React permite **visualizar dispositivos, criar domínios, criar perfis, cadastrar dispositivos, associar perfis e visualizar medições com classificação**. Os dados são consultados na API e no PostgreSQL existentes; o painel não usa dados simulados fixos para seus indicadores.

> **Não é produção.** API sem autenticação, MQTT anônimo, dados do PostgreSQL sem autorização real por tenant, credenciais demonstrativas, tráfego HTTP e SQLite sem criptografia. **Somente localhost e dados sintéticos.** Um usuário que conheça outro identificador de inquilino poderá consultá-lo. O filtro de tela **não implementa** RF-SEG-03.

## Alterações técnicas

- `GET /api/v1/catalogo/dominios?inquilino=<id>` — lista nomes configurados para o inquilino declarado.
- `GET /api/v1/dispositivos?inquilino=<id>&limite=100` — inventário filtrado por inquilino informado; limite 1–500 (não equivale a paginação RF-APP-07).
- CORS local expandido para `localhost:5173` e `127.0.0.1:5173`; continua restrito à origem da interface de desenvolvimento.
- Interface React dividida em **Visão geral**, **Dispositivos**, **Perfis** e **Histórico**.
- A tela de domínio/perfil chama os endpoints HTTP já existentes da versão 0.2.0; no vínculo valida compatibilidade de domínio no backend.
- Indicadores de qualidade baseados nas **até 500 leituras retornadas** do dispositivo selecionado; NÃO refletem toda a frota nem o histórico completo.
- Não houve alteração das tabelas existentes na versão 0.3.0. Dados persistidos no volume PostgreSQL permanecem.

## Atualização sobre a v0.2.0 no Arch Linux

1. (Recomendado) Faça backup do volume e do código caso tenha alterações locais. Exemplo:

   ```bash
   cd ~/Projetos/IoT/Plataforma_IoT_Integrada_ArchLinux
   mkdir -p backups
   docker compose -f infra/compose.lab.yml exec -T db pg_dump -U iot_lab -d iot_laboratorio > "backups/iot-antes-v030-$(date +%Y%m%d-%H%M%S).sql"
   ls -lh backups/iot-antes-v030-*.sql
   ```

   Se já existirem vários backups, inspecione o mais recente e considere testar a restauração em uma instância separada. Não registre backups no Git.

2. Extraia o **ZIP incremental v0.3.0** na pasta-pai `~/Projetos/IoT` (o ZIP inclui o diretório `Plataforma_IoT_Integrada_ArchLinux/`). Isso **sobrescreve** os arquivos de código modificados; se você os editou, use Git/diff antes de atualizar.
3. Inicie novamente a API (preservando os volumes):

   ```bash
   ./scripts/linux/01-iniciar-laboratorio.sh
   ```

4. Abra o painel com um único comando:

   ```bash
   ./scripts/linux/07-iniciar-painel.sh
   ```

   **Painel:** http://127.0.0.1:5173  •  **Swagger:** http://127.0.0.1:8000/docs

   O script `07` chama `npm install` na primeira execução e inicia o Vite; deixe o terminal aberto durante o uso. Requer `nodejs`, `npm` e conectividade de rede para instalar dependências na primeira execução.

5. Para verificar os endpoints e testes Python em uma operação (opcional):

   ```bash
   ./scripts/linux/08-validar-painel.sh
   ```

   Esta validação é **somente leitura** e não modifica os dispositivos registrados.

## Fluxo resumido pela interface

1. Selecione o inquilino `coop-cerrado` e clique **Aplicar**.
2. Na **Visão geral**, veja os dispositivos e as últimas medições.
3. Em **Perfis**, consulte `solo-lab-v02` ou crie um perfil novo associado a um domínio existente.
4. Em **Dispositivos**, associe o perfil ao sensor; leituras anteriores não são reclassificadas.
5. Em **Histórico**, selecione o dispositivo e filtre por `suspeita`, `conforme` ou `nao_avaliada`.

## O que não foi implementado nesta versão

- Usuários, OIDC/MFA, autenticação de dispositivo e autorização multi-inquilino real.
- Regras de alarme, notificações, comandos, NGSI-LD, DLQ, dados abertos e consultas espaciais.
- Histórico paginado, métricas gerais por organização e painéis totalmente configuráveis.
- Testes RNF de carga, latência, 72 horas de borda, TLS, durabilidade ponta a ponta e disponibilidade.

A versão 0.3.0 melhora a **usabilidade demonstrativa** sem afirmar o atendimento integral de RF-APP-04/06 ou dos demais requisitos da atividade.
