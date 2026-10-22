# Atalhos de execução no Arch Linux

| Arquivo | Função |
|---|---|
| `00-verificar-ambiente.sh` | Inspeciona pacotes e acesso ao Docker, sem alterar sistema |
| `01-iniciar-laboratorio.sh` | Inicializa API, banco, borda e broker via Compose |
| `02-demonstrar-fluxo.sh` | Envia dados sintéticos e confere histórico |
| `03-teste-desconexao.sh` | Executa o ensaio que interrompe e restaura a API central |
| `04-encerrar-laboratorio.sh` | Encerra contêineres e preserva volumes |
| `05-demo-mqtt.sh` | Instala cliente MQTT em venv e envia leitura de laboratório |
| `06-demonstrar-perfis.sh` | Exercita os perfis e a qualidade de medições |
| `07-iniciar-painel.sh` | Instala dependências npm quando necessário e inicia React |
| `08-validar-painel.sh` | Testa os novos endpoints e regras Python sem alterar dados |

Executar desde qualquer diretório, chamando o caminho absoluto se necessário. Os scripts mudam para a raiz do projeto internamente. Leia `docs/05-arch-linux.md` antes de usar.
| `18-validar-observabilidade.sh` | Valida resumo por organização e permissões de métricas, sem alterar registros |
| `19-atualizar-v070.sh` | Backup e reconstrução v0.7.0 preservando o modo aberto ou JWT de laboratório |
