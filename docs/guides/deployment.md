# Deploy em Produção

## Pré-requisitos

- Sistema Linux com systemd
- Rust compilado (`cargo build --workspace --release`)
- Python 3.11+ para os serviços Python
- (Opcional) SQLite para persistência

## Binários

```bash
# Compilar em modo release
cargo build --workspace --release

# Binários produzidos:
# target/release/leet          — CLI / MCP backend
# target/release/leet-server   — serviço gRPC
# target/release/leet-agent    — cliente de agente standalone
```

## Configuração via Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LEET_PORT` | `50051` | Porta gRPC do leet-server |
| `LEET_STORE` | `memory` | Backend de storage: `memory` ou `sqlite` |
| `LEET_SQLITE_PATH` | `.leet_store.db` | Caminho do banco SQLite |
| `LEET_LOG` | `info` | Nível de log (`debug`, `info`, `warn`, `error`) |
| `LEET_W_PATH` | — | Caminho da W matrix calibrada (`W.bin`) |
| `LEET_API_KEY` | — | API key para modo `leet chat` |

## Systemd — leet-server

Arquivo de unit: `/etc/systemd/system/leet-server.service`

```ini
[Unit]
Description=1337 leet-service gRPC server
After=network.target

[Service]
Type=simple
User=leet
WorkingDirectory=/opt/leet
ExecStart=/opt/leet/leet-server
Environment=LEET_PORT=50051
Environment=LEET_STORE=sqlite
Environment=LEET_SQLITE_PATH=/var/lib/leet/store.db
Environment=LEET_LOG=info
Environment=LEET_W_PATH=/opt/leet/W.bin
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Instalar
sudo cp target/release/leet-server /opt/leet/
sudo useradd -r -s /sbin/nologin leet
sudo mkdir -p /var/lib/leet && sudo chown leet:leet /var/lib/leet

# Ativar
sudo systemctl daemon-reload
sudo systemctl enable leet-server
sudo systemctl start leet-server
sudo systemctl status leet-server
```

## Systemd — MCP Server (Claude Code)

Arquivo de unit: `/etc/systemd/system/leet-mcp.service`

```ini
[Unit]
Description=1337 MCP server para Claude Code
After=network.target

[Service]
Type=simple
User=<seu-usuario>
WorkingDirectory=/home/<seu-usuario>/1337
ExecStart=/usr/bin/python3 mcp/leet_mcp.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Verificação de Saúde

```bash
# Via CLI
./target/release/leet health
./target/release/leet health --url 192.168.1.10:50051

# Via systemd
sudo systemctl status leet-server
sudo journalctl -u leet-server -f   # logs em tempo real
```

## SQLite vs Memory

| | Memory | SQLite |
|-|--------|--------|
| Persistência | Reinicialização apaga dados | Persiste entre reinicializações |
| Performance | Mais rápido | Levemente mais lento |
| Uso | Dev, testes | Produção |
| Configuração | `LEET_STORE=memory` | `LEET_STORE=sqlite` |

## W Matrix em Produção

Para projeção semântica de alta qualidade, forneça a W matrix calibrada:

```bash
# Copiar W.bin para o servidor
scp calibration/data/W.bin servidor:/opt/leet/W.bin

# Configurar no systemd
Environment=LEET_W_PATH=/opt/leet/W.bin
```

Sem `W.bin`, o leet-bridge usa o `MockProjector` com heurísticas de palavras-chave. Consulte [Calibração](calibration.md) para gerar uma W matrix customizada.

## Múltiplos Agentes

Cada agente se identifica com um `agent_id` único. O store namespacing é feito por `agent_id`:

```bash
# Agente 1
LEET_API_KEY=... ./target/release/leet-agent --id "agente-prod-1" --server localhost:50051

# Agente 2
LEET_API_KEY=... ./target/release/leet-agent --id "agente-prod-2" --server localhost:50051
```

## Logs

```bash
# Nível de detalhe
LEET_LOG=debug leet-server    # inclui cada operação de projeção
LEET_LOG=warn  leet-server    # apenas warnings e erros

# Com journald
sudo journalctl -u leet-server --since "1 hour ago"
```

## Segurança

- O leet-service não tem autenticação nativa — use firewall ou tunelamento SSH para restringir acesso
- `LEET_API_KEY` não deve ser commitado — use variáveis de ambiente do systemd ou um secrets manager
- Permissões do banco SQLite: `chmod 600 /var/lib/leet/store.db`
