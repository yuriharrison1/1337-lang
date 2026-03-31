# 1337 Service — Container Docker
#
# Build: docker build -t leet-service .
# Run:   docker run -p 50051:50051 leet-service
#
# Multi-stage build para imagem otimizada

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: Builder
# ═══════════════════════════════════════════════════════════════════════════════
FROM rust:1.75-slim-bookworm AS builder

WORKDIR /build

# Instala dependências de build
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia workspace Rust
COPY leet1337/Cargo.toml leet1337/Cargo.lock ./
COPY leet1337/leet-core ./leet-core
COPY leet1337/leet-bridge ./leet-bridge
COPY leet1337/leet-service ./leet-service

# Build release
RUN cargo build --release -p leet-service

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: Runtime
# ═══════════════════════════════════════════════════════════════════════════════
FROM debian:bookworm-slim AS runtime

WORKDIR /app

# Instala dependências runtime
RUN apt-get update && apt-get install -y \
    libzmq3-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN useradd -m -u 1000 -s /bin/bash leet

# Copia binário do builder
COPY --from=builder /build/target/release/leet-service /app/leet-service

# Portas expostas
# 50051 — gRPC
# 5555-5558 — ZeroMQ
EXPOSE 50051 5555 5556 5557 5558

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD /app/leet-service --health-check || exit 1

# Switch para usuário não-root
USER leet

# Variáveis de ambiente padrão
ENV LEET_PORT=50051
ENV LEET_BACKEND=simd
ENV LEET_STORE=memory
ENV LEET_LOG_LEVEL=info
ENV RUST_LOG=info

ENTRYPOINT ["/app/leet-service"]
