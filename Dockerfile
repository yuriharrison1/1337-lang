# 1337 Service — Container Docker
#
# Build: docker build -t leet-service .
# Run:   docker run -p 50051:50051 leet-service
#
# Multi-stage build for an optimized image

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: Builder
# ═══════════════════════════════════════════════════════════════════════════════
FROM rust:1.75-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the Rust workspace
COPY Cargo.toml Cargo.lock ./
COPY leet-core ./leet-core
COPY leet-bridge ./leet-bridge
COPY leet-service ./leet-service

# Build release
RUN cargo build --release -p leet-service

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: Runtime
# ═══════════════════════════════════════════════════════════════════════════════
FROM debian:bookworm-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libzmq3-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash leet

# Copy the binary from the builder
COPY --from=builder /build/target/release/leet-service /app/leet-service

# Exposed ports
# 50051 — gRPC
# 5555-5558 — ZeroMQ
EXPOSE 50051 5555 5556 5557 5558

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD /app/leet-service --health-check || exit 1

# Switch to non-root user
USER leet

# Default environment variables
ENV LEET_PORT=50051
ENV LEET_BACKEND=simd
ENV LEET_STORE=memory
ENV LEET_LOG_LEVEL=info
ENV RUST_LOG=info

ENTRYPOINT ["/app/leet-service"]
