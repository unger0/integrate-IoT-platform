# Ajuste da interface de autenticação — v0.5.1 (Arch Linux)

**Escopo:** interface React e ferramentas de diagnóstico local. A API continua na versão 0.5.0. **Nenhuma tabela do banco é alterada** e os dados existentes são preservados.

## O que foi observado

Na captura do painel, a faixa amarela indicava modo JWT didático ativo e a faixa vermelha dizia `Authorization: Bearer <token> obrigatório`. O contador de regras estava em zero e o seletor não tinha dispositivos porque as listagens exigiam autenticação. A barra lateral dizia `API indisponível`, embora a API pudesse estar online: o frontend confundia HTTP 401 (não autorizado) com falha de rede.

## O que mudou

- O frontend primeiro consulta `/health` e identifica se o backend está em modo aberto ou JWT.
- Se JWT estiver habilitado e ainda não houver token, as consultas protegidas aguardam; é exibido `API online · autenticação pendente`.
- Ao colar o token, o frontend faz `GET /api/v1/identidade` e **só então** libera as consultas.
- O inquilino é preenchido com a organização reconhecida no token, evitando confusão com uma organização que o usuário não pode acessar.
- Tokens inválidos ou expirados deixam uma mensagem específica. O token é guardado somente em memória e apagado do campo após validação; ao recarregar a página será necessário inseri-lo de novo.
- Corrige apenas a distinção e a UX de autenticação; **não implementa OIDC, MFA ou TLS**.

## Instalação incremental

Na pasta raiz do projeto instalado:

```bash
unzip -o ~/Downloads/IoT_ArchLinux_correcao_painel_v0.5.1.zip -d ~/Projetos/IoT/
cd ~/Projetos/IoT/Plataforma_IoT_Integrada_ArchLinux
./scripts/linux/14-verificar-acesso-painel.sh
```

Se o token tiver expirado, renove **sem reiniciar os serviços**:

```bash
./scripts/linux/15-renovar-token-gestor.sh
./scripts/linux/14-verificar-acesso-painel.sh
```

Acesse `http://127.0.0.1:5173` com o Vite ativo (`./scripts/linux/07-iniciar-painel.sh`). Cole o token obtido **localmente** no arquivo `runtime/token-gestor.txt` e clique em **Validar e entrar**. Não coloque tokens em mensagens, screenshots, commits ou sistemas externos.

Se for necessário construir/verificar o frontend:

```bash
cd apps/web
npm install
npm run build
```

Isso verifica a compilação no seu notebook. Atualização de frontend Vite costuma ser refletida automaticamente se o servidor de desenvolvimento já estiver ativo.

## O que o diagnóstico não prova

O script `14` testa conectividade HTTP, modo da API, validade do JWT e permissão de consulta. Não testa HTTPS, isolamento completo, revogação de tokens, autenticação de dispositivo, ACL MQTT ou conformidade com os RNFs. Esta versão segue sendo um **laboratório local com dados fictícios**.
