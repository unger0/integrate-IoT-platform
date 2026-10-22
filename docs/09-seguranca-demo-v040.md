# v0.4.0 — Autorização demonstrativa por organização e papel

> **Estado:** laboratório restrito a `127.0.0.1`, com dados sintéticos. NÃO é produto seguro nem equivale a OIDC/OAuth2, MFA, TLS, X.509, autenticação MQTT ou criptografia da fila.

## Motivação

O painel v0.3 tinha um campo de organização (`inquilino`) que era somente um filtro. Qualquer pessoa com acesso à API podia escolher outra organização e consultar dados. O novo modo JWT demonstrativo torna o acesso dependente de uma **identidade assinada**, contendo `sub` (identidade), `tenant` (organização), `role` (papel), `iat`, `exp`, `iss`, `aud` e `jti`.

A assinatura é verificada com **HS256** e uma chave local aleatória de pelo menos 32 bytes. A API verifica assinatura, emissor, destinatário e expiração. Nunca confie em um tenant enviado apenas pelo navegador. O backend verifica que a organização solicitada corresponde ao token, inclusive ao consultar histórico e estado por ID de dispositivo.

**Atenção:** o script de emissão usa uma chave compartilhada local. Não há servidor de identidade, gerenciamento de contas nem MFA. Em produção, precisaremos substituir isso por OIDC e validadores JWT com JWKS e assinaturas assimétricas, além de HTTPS, rotação e revogação.

## Matriz simplificada de papéis (somente demonstração)

| Papel | Consultar dados da própria organização | Cadastrar domínio/perfil | Cadastrar dispositivo | Transmitir telemetria |
|---|---|---|---|---|
| administrador | Sim | Sim | Sim | Sim |
| gestor | Sim | Sim | Sim | Sim |
| integrador | Sim | Não | Sim | Sim |
| operador | Sim | Não | Não | Não |
| leitor | Sim | Não | Não | Não |
| borda | Não | Não | Não | Sim, na organização do token |
| dispositivo | Não | Não | Não | Sim, apenas seu `device_id` |

Não há administrador global. Mesmo o papel `administrador` está vinculado a um único tenant neste modo de demonstração. Cada papel é conferido no backend.

## Execução no Arch Linux

Na raiz do projeto, com a API v0.4 aberta:

```bash
./scripts/linux/01-iniciar-laboratorio.sh
```

Isso mantém o laboratório antigo, sem autenticação, para compatibilidade.

Para habilitar o modo demonstrativo de segurança:

```bash
./scripts/linux/09-iniciar-protegido.sh
./scripts/linux/10-validar-autorizacao.sh
```

O primeiro script:

1. cria `IOT_LAB_JWT_SECRET` em `.env.protegido`, sem incluir a chave no ZIP;
2. gera tokens temporários para o nó de borda, a ponte MQTT e um gestor da `coop-cerrado`;
3. recria os contêineres `api` e `edge` com a sobreposição `infra/compose.auth-demo.yml`;
4. guarda o token do gestor em `runtime/token-gestor.txt` (não compartilhe esse arquivo).

O segundo script executa testes unitários e verifica HTTP: acesso sem token recebe 401, organização não autorizada recebe 403 e organização correta recebe 200. O token do gestor expira após uma hora. O token da borda expira após oito horas; execute novamente o script 09 para renovar ambos. Se a ponte MQTT experimental estiver ativa, reinicie-a usando a sobreposição autenticada antes de enviar dados por MQTT.

Abra o painel com:

```bash
./scripts/linux/07-iniciar-painel.sh
```

No campo **Token de acesso (laboratório)**, cole o conteúdo de `runtime/token-gestor.txt` e pressione **Usar token**. O token não é salvo em `localStorage` nem em cookies, permanece somente em memória durante a sessão da aba.

**Para voltar aos scripts originais, que não enviam tokens:**

```bash
./scripts/linux/11-restaurar-laboratorio.sh
```

Esses comandos **não apagam** os volumes de PostgreSQL e SQLite. Nunca use `down -v` se quiser preservar medições anteriores.

## O que falta para completar os requisitos de segurança do PDF?

- RF-SEG-01: OpenID Connect/OAuth2, MFA dos administradores e ciclo completo de sessões.
- RF-SEG-02: políticas RBAC completas, administração, testes de endpoints e revisão do modelo de papéis; esta versão é só uma demonstração.
- RF-SEG-03: isolamento robusto em todas as rotas, testes entre múltiplas organizações, políticas de banco/RLS e análise de segurança.
- RF-SEG-04: autenticação por dispositivo e autorização de tópicos MQTT na central e borda, incluindo TLS.
- RF-SEG-05: credenciais individuais para nós de borda e criptografia da fila em repouso.
- RNF-11: TLS em todas as interfaces externas, segredos protegidos em repouso e rotação.

Na simulação, uma identidade local que detenha a chave de assinatura poderia emitir tokens arbitrários; essa chave deve permanecer privada. Um usuário com acesso ao Docker Engine também pode obter privilégio elevado. Não expor os serviços na rede e não cadastrar informações reais.

## Validações realizadas na preparação

Executados 22 testes locais de lógica e HTTP (incluindo 10 novos testes de segurança) com substituição simulada da conexão com o banco. Verificação de sintaxe Python e Bash. O funcionamento completo da imagem Docker, instalação npm e comunicação com PostgreSQL no Arch Linux precisa ser reproduzido no notebook.
