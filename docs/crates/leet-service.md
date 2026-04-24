# leet-service

Serviço gRPC/TCP Rust que expõe operações COGON sobre a rede. Centraliza projeção e armazenamento para agentes distribuídos.

## Arquitetura

```
Agentes → gRPC (porta 50051) → LeetServiceImpl
                                   ├── Engine (projeção via W matrix)
                                   ├── Store  (memory | sqlite)
                                   └── BatchQueue (encode em lote)
```

## Binários

```bash
# Servidor gRPC
cargo run --bin leet-server

# Cliente de agente (modo standalone)
cargo run --bin leet-agent
```

## Configuração

Todas as opções via variáveis de ambiente:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LEET_PORT` | `50051` | Porta gRPC |
| `LEET_STORE` | `memory` | Backend de storage (`memory` ou `sqlite`) |
| `LEET_SQLITE_PATH` | `.leet_store.db` | Caminho do banco SQLite |
| `LEET_LOG` | `info` | Nível de log |
| `LEET_W_PATH` | — | Caminho da W matrix (ver leet-bridge) |

```bash
LEET_STORE=sqlite LEET_SQLITE_PATH=/data/leet.db ./leet-server
```

## API gRPC

Proto: `leet.proto` (incluso via `tonic::include_proto!("leet")`).

### `Encode`

Projeta texto em COGON e persiste no store.

```protobuf
rpc Encode(EncodeRequest) returns (EncodeResponse);

message EncodeRequest {
    string text     = 1;
    string agent_id = 2;
}

message EncodeResponse {
    string  cogon_id      = 1;
    repeated float sem    = 2;  // 32 valores
    int64   stamp         = 3;  // Unix ms
    int64   tokens_saved  = 4;  // estimativa de tokens economizados
}
```

### `EncodeBatch`

Streaming bidirecional — envia vários textos, recebe COGONs à medida que ficam prontos.

```protobuf
rpc EncodeBatch(stream EncodeRequest) returns (stream EncodeResponse);
```

### `Decode`

Reconstrói texto a partir de um vetor sem.

```protobuf
rpc Decode(DecodeRequest) returns (DecodeResponse);

message DecodeRequest {
    repeated float sem = 1;
    string lang        = 2;  // "pt" | "en"
}
```

### `Delta`

Calcula diferença entre dois vetores sem. Retorna patch e magnitude normalizada por `√32 → [0, 1]`.

```protobuf
rpc Delta(DeltaRequest) returns (DeltaResponse);

message DeltaResponse {
    repeated float patch = 1;
    float magnitude      = 2;  // [0, 1]
}
```

### `Recall`

Busca semântica no store do agente — retorna os k COGONs mais próximos.

```protobuf
rpc Recall(RecallRequest) returns (RecallResponse);

message RecallRequest {
    string agent_id    = 1;
    repeated float sem = 2;
    int32  k           = 3;
}
```

### `Health`

Status do serviço.

```protobuf
rpc Health(HealthRequest) returns (HealthResponse);

message HealthResponse {
    string status  = 1;  // "ok"
    string backend = 2;  // "memory" | "sqlite"
    int64  uptime  = 3;  // segundos
}
```

## Store

### Memory Store

Store em memória — padrão, sem persistência entre reinicializações. Ideal para desenvolvimento e testes.

### SQLite Store

Persistência em disco. Cada agente tem sua própria tabela de COGONs indexados por `(agent_id, cogon_id, stamp)`.

```bash
LEET_STORE=sqlite leet-server
```

## BatchQueue

Queue interna para processar múltiplos encodes de forma eficiente. Configurada automaticamente pelo `LeetServiceImpl`.

## Módulos

| Módulo | Responsabilidade |
|--------|------------------|
| `server` | Implementação do trait `LeetService` (tonic) |
| `tcp_server` | Wrapper TCP raw (alternativa ao gRPC) |
| `projection` | Engine de projeção — wrapping do leet-bridge |
| `store` | Trait `Store` + backends memory e sqlite |
| `batch` | `BatchQueue` para encode em lote |
| `config` | Leitura de env vars |
| `agent_client` | Cliente gRPC para conexão de agentes ao serviço |

## Verificar Status

```bash
leet health                           # localhost:50051
leet health --url 192.168.1.10:50051  # host remoto
```

## Testes

```bash
cargo test -p leet-service   # 22 testes
```
