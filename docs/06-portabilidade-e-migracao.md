# Portabilidade do projeto — Windows → Arch Linux

## Não é necessário começar de novo

A base já usa contêineres Linux para API, borda e MQTT. O PostgreSQL é executado em contêiner; os simuladores usam apenas a biblioteca padrão do Python; o painel utiliza React. Portanto, **o código existente foi preservado** e a adaptação foi feita sobretudo na execução, documentação e automação.

## Mapeamento rápido de comandos

| Ação | Windows PowerShell | Arch Linux (bash/zsh) |
|---|---|---|
| Entrar na pasta | `cd C:\...\projeto` | `cd ~/Projetos/IoT/Plataforma_IoT_Integrada_ArchLinux` |
| Descompactar | `Expand-Archive ...` | `unzip ...` |
| Executar Python | `py -3 scripts/demo_central.py` | `python scripts/demo_central.py` |
| Criar ambiente virtual | `py -3 -m venv .venv` | `python -m venv .venv` |
| Instalar dependência | `.venv\Scripts\python.exe -m pip install paho-mqtt` | `.venv/bin/python -m pip install paho-mqtt` |
| API + banco + borda | `docker compose -f infra/compose.lab.yml up --build -d` | **Igual** |
| Serviços e logs | `docker compose ... ps/logs` | **Igual** |
| Frontend | `cd apps/web; npm install; npm run dev` | `cd apps/web && npm install && npm run dev` |

## Se você ainda NÃO executou o laboratório no Windows

Use diretamente a nova pasta no Arch. Não há banco antigo a migrar e não há necessidade de mexer em volumes Docker. Execute apenas os comandos do guia `05-arch-linux.md`.

## Se já existem dados persistidos no Windows

**Atenção:** mover o código não transfere os volumes Docker. Em especial, os dados do PostgreSQL e da borda devem ser transferidos separadamente e com consistência. Não copie a pasta interna do volume de banco de um sistema para o outro.

Para salvar o banco central do laboratório a partir da pasta original no Windows, com os serviços ativos, exemplo no PowerShell:

```powershell
docker compose -f infra/compose.lab.yml exec -T db pg_dump -U iot_lab -d iot_laboratorio --no-owner --no-privileges > backup_iot.sql
```

Antes de restaurar, confirme que o banco de destino é **novo e vazio** e que o dump não contém dados sensíveis. No Arch, pela raiz do novo projeto, exemplo:

```bash
docker compose -f infra/compose.lab.yml exec -T db psql -v ON_ERROR_STOP=1 -U iot_lab -d iot_laboratorio < backup_iot.sql
```

**Cuidado com a restauração:** as tabelas básicas são criadas quando a API inicializa. Uma restauração SQL em banco não vazio pode produzir conflitos. Planeje a sequência de inicialização e restauração em ambiente descartável ou peça ajuda antes de substituir qualquer dado existente.

A fila SQLite da borda requer **backup próprio, feito com a borda parada ou com o mecanismo de backup do SQLite**, e restauração no volume `edgequeue`. É deliberadamente omitido um comando de cópia cega, que poderia gerar perda de dados. Se não houver mensagens pendentes, basta permitir que a central mantenha o histórico, reinicializando a fila no novo ambiente.

**Não copie** `.venv`, `node_modules` nem binários instalados no Windows: devem ser recriados no Arch. Os arquivos `.py`, `.tsx`, `.json`, `.yml`, `.md` podem ser levados normalmente.

## Registro de alteração

- Sistema-alvo alterado para Arch Linux com Docker Engine + systemd.
- Adicionados scripts Bash de checagem, inicialização, simulação, desconexão e encerramento.
- Adicionados scripts Python portáveis de validação e ensaio offline.
- O contrato canônico, os requisitos funcionais e a arquitetura central/borda foram mantidos sem mudanças conceituais.
- Os arquivos do projeto original não foram sobrescritos: a entrega está em um pacote novo.
