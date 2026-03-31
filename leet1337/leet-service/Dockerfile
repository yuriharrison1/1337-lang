FROM rust:1.75-alpine AS builder
RUN apk add --no-cache musl-dev protobuf-dev
WORKDIR /app
COPY . .
RUN cargo build --release -p leet-service

FROM alpine:latest
RUN apk add --no-cache libgcc
COPY --from=builder /app/target/release/leet-service /usr/local/bin/
EXPOSE 50051
CMD ["leet-service"]
