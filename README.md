# Plataforma IoT Integrada — Laboratório v0.7.0 (Arch Linux)

**Novo:** aba **Observabilidade**, resumo histórico por organização, exportador Prometheus
com acesso global restrito no JWT demonstrativo e logs JSON com ID de correlação.
Não inclui stack Prometheus/Grafana ou rastreamento distribuído completo.

- Aplicar pacote incremental: `IoT_ArchLinux_atualizacao_v0.7.0.zip` sobre a pasta existente.
- Atualizar com backup e testes: `./scripts/linux/19-atualizar-v070.sh`.
- Verificação somente-leitura: `./scripts/linux/18-validar-observabilidade.sh`.
- Abrir painel: `./scripts/linux/07-iniciar-painel.sh`, opção **Observabilidade**.
- Guia: [docs/13-observabilidade-v070.md](docs/13-observabilidade-v070.md).

**Continua sendo laboratório local com dados sintéticos.** Não exponha a API ou o broker
à Internet. O token JWT local não é OIDC/MFA e a fila da borda ainda não é criptografada.

---

# Plataforma IoT Integrada — Laboratório v0.6.0 (Arch Linux)

**Evolução v0.6.0: diagnóstico da pontualidade dos dispositivos.** A aba **Operação** mostra quais dispositivos enviaram leituras recentemente, quais estão atrasados, sem dados, sem perfil ou com timestamp inconsistente. O cálculo utiliza o horário da medição e o intervalo configurado no perfil (tolerância de 2× o intervalo); **não comprova se o equipamento está conectado à rede**. O resultado é apenas para laboratório, não gera alarmes e não modifica o banco.

- Atualização incremental: `IoT_ArchLinux_atualizacao_v0.6.0.zip`, extraída sobre a pasta existente.
- Aplicar e verificar: `./scripts/linux/17-atualizar-v060.sh` (backup antes da reconstrução).
- Repetir verificação somente-leitura: `./scripts/linux/16-validar-operacao.sh`.
- Interface: `./scripts/linux/07-iniciar-painel.sh` (se já estava em execução, recarregue a página).
- Documentação: [docs/12-estado-dispositivos-v060.md](docs/12-estado-dispositivos-v060.md).

A API continua em modo aberto ou JWT demonstrativo, conforme sua instalação. **Não é uma implementação de OIDC, MFA ou segurança de produção.** Não use com equipamentos físicos ou dados reais.

---

# Plataforma IoT Integrada — Laboratório v0.5.0 + Interface v0.5.1 (Arch Linux)

**Nova versão:** regras configuráveis de limiar e alarmes com reconhecimento/resolução no painel. Preserva ingestão HTTP, MQTT experimental, nó de borda SQLite, PostgreSQL, perfis de dispositivo, painel React e JWT didático opcional das versões anteriores.

**Interface v0.5.1:** distingue erro de conexão de token pendente, valida o token antes de carregar dados e apresenta diagnóstico somente-leitura. Veja [docs/11-painel-acesso-v051.md](docs/11-painel-acesso-v051.md).

**Guia de atualização e limitações:** [docs/10-motor-de-regras-v050.md](docs/10-motor-de-regras-v050.md).

## Atualizar a instalação existente (v0.4 → v0.5)

```bash
unzip -o ~/Downloads/IoT_ArchLinux_atualizacao_v0.5.0.zip -d ~/Projetos/IoT/
cd ~/Projetos/IoT/Plataforma_IoT_Integrada_ArchLinux
./scripts/linux/13-atualizar-v050.sh  # cria backup e preserva modo aberto/JWT demonstrativo
./scripts/linux/12-demonstrar-alarmes.sh
```

Se a API antiga estiver desligada, o script 13 pedirá para iniciá-la antes. Se estava em modo JWT, o script renova o token de `runtime/token-gestor.txt`.

Painel: `http://127.0.0.1:5173` (execute `./scripts/linux/07-iniciar-painel.sh` em um terminal) · Swagger: `http://127.0.0.1:8000/docs`.

**Atenção:** isto ainda é um laboratório, sem OIDC, MFA, TLS, ACL MQTT ou proteção de produção. Não exponha o servidor à Internet nem conecte atuadores reais.

---

## Continuar o laboratório 0.3 (compatível)

```bash
./scripts/linux/01-iniciar-laboratorio.sh
./scripts/linux/07-iniciar-painel.sh
```

Swagger: http://127.0.0.1:8000/docs · Painel: http://127.0.0.1:5173

## Testar autorização por organização (opcional)

```bash
./scripts/linux/09-iniciar-protegido.sh
./scripts/linux/10-validar-autorizacao.sh
```

O script 09 cria automaticamente uma chave local e tokens temporários, guardados em arquivos ignorados pelo Git. Para entrar no painel no modo de demonstração, copie o conteúdo de `runtime/token-gestor.txt` para o campo **Token de acesso** (não envie esse token por chat). O arquivo expira em uma hora; para renová-lo, execute novamente o script 09. Use apenas no seu notebook com dados fictícios.

Para restaurar o modo aberto que executa os scripts antigos:

```bash
./scripts/linux/11-restaurar-laboratorio.sh
```

## Limites conhecidos

- Contêineres vinculados ao endereço local 127.0.0.1; não publicar na Internet.
- JWT HS256 emitido localmente, **sem login, OpenID Connect, MFA, revogação nem TLS**.
- Fila SQLite da borda sem criptografia em repouso; MQTT de laboratório sem ACL/TLS.
- Scripts antigos sem token não funcionam no modo protegido; use o modo aberto ou inclua autenticação na futura integração.
- Testes unitários e smoke-tests didáticos não comprovam durabilidade 72h, escalabilidade nem RNFs da especificação.
- O banco e as filas são mantidos nos volumes Docker; evite `docker compose down -v`.

Consulte também [docs/05-arch-linux.md](docs/05-arch-linux.md) e [docs/08-painel-v030.md](docs/08-painel-v030.md) para entender os serviços existentes.
