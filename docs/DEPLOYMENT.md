# Deployment — 1337

## Visão geral

O 1337 pode ser implantado de três formas:

| Modo | Componentes | Caso de uso |
|------|------------|-------------|
| **CLI standalone** | `leet` + `LEET_API_KEY` | Uso pessoal, scripts |
| **Servidor local** | `leet-server` + `leet-agent` × N | Dev/staging, rede local |
| **Produção (systemd)** | `leet-service.service` + `leet-agent@.service` | Servidores Linux |

---

## Compilação para produção

```bash
cargo build --release -p leet-cli -p leet-service

# Binários gerados:
ls -la target/release/leet target/release/leet-server target/release/leet-agent
```

---

## Modo servidor local (desenvolvimento)

```bash
# Terminal 1: iniciar servidor
./target/release/leet-server --tcp 127.0.0.1:1337

# Terminal 2: conectar agentes
for agent in ATLAS RAVEN TENSOR PULSE FORGE; do
    LEET_API_KEY=$LEET_API_KEY \
    ./target/release/leet-agent --name "$agent" --llm anthropic &
done

# Terminal 3: chat
LEET_API_KEY=$LEET_API_KEY ./target/release/leet chat --connect 127.0.0.1:1337
```

---

## Deployment systemd (produção)

### Pré-requisitos

- Linux com systemd
- Rust toolchain (para compilar)
- `sudo` com privilégios

### Setup automático

```bash
sudo bash deploy/systemd/setup.sh
```

O script executa:
1. Cria usuário `leet` (sem shell, sem home)
2. Cria diretórios: `/etc/leet/`, `/etc/leet/agents/`, `/var/log/leet/`
3. Gera arquivos de role para cada agente em `/etc/leet/agents/<NOME>.role`
4. Cria `/etc/leet/env` (arquivo de ambiente — edite para adicionar `LEET_API_KEY`)
5. Compila com `cargo build --release`
6. Copia binários para `/usr/local/bin/`
7. Instala e habilita `leet-service.service`

### Configurar a chave API

```bash
sudo nano /etc/leet/env
```

Adicione:
```bash
LEET_API_KEY=sk-ant-...
LEET_MODEL=claude-haiku-4-5-20251001
RUST_LOG=info
```

```bash
sudo chmod 600 /etc/leet/env
sudo chown leet:leet /etc/leet/env
```

### Gerenciar o serviço

```bash
# Iniciar servidor
sudo systemctl start leet-service
sudo systemctl status leet-service

# Iniciar agentes individualmente
sudo systemctl start leet-agent@ATLAS
sudo systemctl start leet-agent@RAVEN
sudo systemctl start leet-agent@TENSOR

# Iniciar todos os 15 agentes
for a in ATLAS CIPHER FORGE NEXUS ORACLE PULSE RAVEN SPARK TENSOR VORTEX ZERO FLUX ECHO DRIFT PRISM; do
    sudo systemctl start leet-agent@$a
done

# Habilitar na inicialização
sudo systemctl enable leet-service
sudo systemctl enable leet-agent@ATLAS  # exemplo

# Recarregar configuração (sem restart)
sudo systemctl reload leet-service

# Parar tudo
sudo systemctl stop 'leet-agent@*'
sudo systemctl stop leet-service
```

### Logs

```bash
# Servidor
journalctl -u leet-service -f

# Agente específico
journalctl -u leet-agent@ATLAS -f

# Todos os agentes
journalctl -u 'leet-agent@*' -f

# Desde o início (com nível debug)
RUST_LOG=debug journalctl -u leet-service --no-pager
```

### Teardown

```bash
sudo bash deploy/systemd/teardown.sh
```

Remove units, para serviços e opcionalmente remove binários.

---

## Estrutura do unit `leet-service.service`

```ini
[Unit]
Description=1337 Translation Service — Semantic Substrate
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/leet-server --tcp 0.0.0.0:1337 --unix /run/leet/leet.sock
Restart=on-failure
RestartSec=5

Environment=RUST_LOG=info
EnvironmentFile=-/etc/leet/env   # opcional, não falha se ausente

RuntimeDirectory=leet            # systemd cria /run/leet automaticamente
User=leet
Group=leet
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict

[Install]
WantedBy=multi-user.target
```

## Estrutura do unit `leet-agent@.service`

O `%i` é substituído pelo nome do agente na instanciação (`leet-agent@ATLAS.service` → `%i=ATLAS`).

```ini
[Unit]
Description=1337 Agent — %i
After=leet-service.service
Requires=leet-service.service
PartOf=leet-service.service

[Service]
Type=simple
ExecStart=/usr/local/bin/leet-agent \
    --name %i \
    --role-file /etc/leet/agents/%i.role \
    --server /run/leet/leet.sock \
    --llm anthropic
Restart=on-failure
RestartSec=10

EnvironmentFile=-/etc/leet/env
User=leet
Group=leet

[Install]
WantedBy=leet-service.service
```

---

## Monitoramento

### Health check

```bash
leet health --url 127.0.0.1:1337
```

### Métricas do servidor

O servidor expõe métricas via log estruturado. Com `RUST_LOG=info`:

```
[INFO] agente ATLAS conectado (id=abc123, total=1)
[INFO] mensagem roteada: ATLAS → broadcast (12 agentes)
[INFO] métricas: total_msgs=1024, agentes_peak=15, nl_tokens=8432
```

### Script de verificação rápida

```bash
#!/bin/bash
# check-leet.sh
echo "=== leet-service ==="
systemctl is-active leet-service

echo "=== Agentes conectados ==="
# conta linhas "conectado" no log dos últimos 5 minutos
journalctl -u leet-service --since "5 min ago" | grep "conectado" | wc -l

echo "=== Health ==="
leet health --url 127.0.0.1:1337 2>/dev/null || echo "não acessível"
```

---

## Segurança

### Isolamento systemd

Os units usam:
- `User=leet` — processo não-root dedicado
- `NoNewPrivileges=true` — impede escalada de privilégio
- `PrivateTmp=true` — `/tmp` isolado
- `ProtectSystem=strict` — sistema de arquivos somente-leitura
- `ReadWritePaths=/run/leet /var/log/leet` — apenas o necessário

### A chave `LEET_API_KEY`

- Armazenada em `/etc/leet/env` com permissão `600` (somente leet)
- Não é logada pelo servidor
- Nunca commitada — adicione `/etc/leet/env` ao `.gitignore`

### Firewall

O `leet-server` escuta em `0.0.0.0:1337` por padrão. Em produção, restrinja:

```bash
# Apenas localhost
leet-server --tcp 127.0.0.1:1337

# Ou firewall
sudo ufw allow from 10.0.0.0/8 to any port 1337
sudo ufw deny 1337
```
