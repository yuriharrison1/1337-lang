"""
Sistema de configuração unificada para o SDK 1337.

Suporta:
- Arquivos de configuração (JSON, YAML, TOML)
- Variáveis de ambiente
- Defaults sensatos
- Validação de configuração
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any, Union


@dataclass
class ServerConfig:
    """Configuração de conexão com servidor."""
    host: str = "localhost"
    port: int = 50051
    timeout: float = 30.0
    use_tls: bool = False
    tls_cert: Optional[str] = None
    
    # Fallbacks
    fallback_hosts: list[str] = field(default_factory=list)


@dataclass
class RetryConfig:
    """Configuração de retry."""
    enabled: bool = True
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    """Configuração de circuit breaker."""
    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3


@dataclass
class CacheConfig:
    """Configuração de cache."""
    enabled: bool = True
    backend: str = "memory"  # 'memory', 'redis', 'sqlite'
    ttl_seconds: float = 3600.0  # 1 hora
    max_size: int = 10000
    
    # Redis-specific
    redis_url: Optional[str] = None
    redis_key_prefix: str = "leet:"
    
    # SQLite-specific
    sqlite_path: Optional[str] = None


@dataclass
class ProjectionConfig:
    """Configuração de projeção semântica."""
    backend: str = "mock"  # 'mock', 'anthropic', 'openai', 'service'
    
    # API keys (preferencialmente via env vars)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Modelos
    anthropic_model: str = "claude-3-haiku-20240307"
    openai_model: str = "gpt-4o-mini"
    
    # Contexto
    context_enabled: bool = True
    default_context_profile: str = "general"


@dataclass
class MetricsConfig:
    """Configuração de métricas."""
    enabled: bool = True
    export_interval_seconds: float = 60.0
    prometheus_port: Optional[int] = None
    
    # Log de métricas
    log_metrics: bool = False
    log_level: str = "INFO"


@dataclass
class LeetConfig:
    """
    Configuração completa do SDK 1337.
    
    Esta é a configuração central que abrange todos os módulos.
    """
    
    # Versão do schema
    version: str = "1.0"
    
    # Módulos de configuração
    server: ServerConfig = field(default_factory=ServerConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    projection: ProjectionConfig = field(default_factory=ProjectionConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    
    # Configurações gerais
    debug: bool = False
    log_level: str = "INFO"
    
    @classmethod
    def from_dict(cls, data: dict) -> "LeetConfig":
        """Cria configuração a partir de dict."""
        # Extrai sub-configs
        server_data = data.pop("server", {})
        retry_data = data.pop("retry", {})
        circuit_data = data.pop("circuit_breaker", {})
        cache_data = data.pop("cache", {})
        projection_data = data.pop("projection", {})
        metrics_data = data.pop("metrics", {})
        
        return cls(
            server=ServerConfig(**server_data),
            retry=RetryConfig(**retry_data),
            circuit_breaker=CircuitBreakerConfig(**circuit_data),
            cache=CacheConfig(**cache_data),
            projection=ProjectionConfig(**projection_data),
            metrics=MetricsConfig(**metrics_data),
            **data
        )
    
    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "LeetConfig":
        """Carrega configuração de arquivo JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "LeetConfig":
        """Carrega configuração de arquivo YAML."""
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return cls.from_dict(data)
        except ImportError:
            raise ImportError("PyYAML não instalado. Instale: pip install pyyaml")
    
    @classmethod
    def from_toml(cls, path: Union[str, Path]) -> "LeetConfig":
        """Carrega configuração de arquivo TOML."""
        try:
            import tomllib
            with open(path, 'rb') as f:
                data = tomllib.load(f)
            return cls.from_dict(data)
        except ImportError:
            try:
                import toml
                with open(path, 'r', encoding='utf-8') as f:
                    data = toml.load(f)
                return cls.from_dict(data)
            except ImportError:
                raise ImportError("TOML library não instalada. Instale: pip install toml")
    
    @classmethod
    def from_env(cls, prefix: str = "LEET_") -> "LeetConfig":
        """
        Carrega configuração de variáveis de ambiente.
        
        Exemplo:
            LEET_SERVER_HOST=localhost
            LEET_SERVER_PORT=50051
            LEET_RETRY_ENABLED=true
            LEET_PROJECTION_BACKEND=anthropic
            LEET_PROJECTION_ANTHROPIC_API_KEY=sk-...
        """
        config = cls()
        
        # Server
        if host := os.environ.get(f"{prefix}SERVER_HOST"):
            config.server.host = host
        if port := os.environ.get(f"{prefix}SERVER_PORT"):
            config.server.port = int(port)
        if timeout := os.environ.get(f"{prefix}SERVER_TIMEOUT"):
            config.server.timeout = float(timeout)
        if fallback := os.environ.get(f"{prefix}SERVER_FALLBACK_HOSTS"):
            config.server.fallback_hosts = fallback.split(",")
        
        # Retry
        if enabled := os.environ.get(f"{prefix}RETRY_ENABLED"):
            config.retry.enabled = enabled.lower() == "true"
        if max_retries := os.environ.get(f"{prefix}RETRY_MAX_RETRIES"):
            config.retry.max_retries = int(max_retries)
        
        # Circuit Breaker
        if enabled := os.environ.get(f"{prefix}CIRCUIT_BREAKER_ENABLED"):
            config.circuit_breaker.enabled = enabled.lower() == "true"
        
        # Cache
        if backend := os.environ.get(f"{prefix}CACHE_BACKEND"):
            config.cache.backend = backend
        if ttl := os.environ.get(f"{prefix}CACHE_TTL_SECONDS"):
            config.cache.ttl_seconds = float(ttl)
        
        # Projection
        if backend := os.environ.get(f"{prefix}PROJECTION_BACKEND"):
            config.projection.backend = backend
        if api_key := os.environ.get(f"{prefix}PROJECTION_ANTHROPIC_API_KEY"):
            config.projection.anthropic_api_key = api_key
        if api_key := os.environ.get(f"{prefix}PROJECTION_OPENAI_API_KEY"):
            config.projection.openai_api_key = api_key
        
        # Metrics
        if enabled := os.environ.get(f"{prefix}METRICS_ENABLED"):
            config.metrics.enabled = enabled.lower() == "true"
        
        # Geral
        if debug := os.environ.get(f"{prefix}DEBUG"):
            config.debug = debug.lower() == "true"
        if log_level := os.environ.get(f"{prefix}LOG_LEVEL"):
            config.log_level = log_level
        
        return config
    
    @classmethod
    def load(
        cls,
        path: Optional[Union[str, Path]] = None,
        env_prefix: str = "LEET_",
        use_env: bool = True
    ) -> "LeetConfig":
        """
        Carrega configuração de arquivo e/ou variáveis de ambiente.
        
        A ordem de precedência (maior prioridade primeiro):
        1. Variáveis de ambiente
        2. Arquivo de configuração
        3. Defaults
        
        Args:
            path: Caminho do arquivo de configuração (JSON, YAML, TOML)
            env_prefix: Prefixo para variáveis de ambiente
            use_env: Se deve carregar de variáveis de ambiente
            
        Returns:
            Configuração carregada
        """
        # Começa com defaults
        config = cls()
        
        # Carrega de arquivo se fornecido
        if path:
            path = Path(path)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo de configuração não encontrado: {path}")
            
            if path.suffix == ".json":
                config = cls.from_json(path)
            elif path.suffix in (".yaml", ".yml"):
                config = cls.from_yaml(path)
            elif path.suffix == ".toml":
                config = cls.from_toml(path)
            else:
                raise ValueError(f"Formato não suportado: {path.suffix}")
        
        # Sobrescreve com variáveis de ambiente
        if use_env:
            env_config = cls.from_env(env_prefix)
            # Merge simples: env sempre vence
            config = _merge_configs(config, env_config)
        
        return config
    
    def to_dict(self) -> dict:
        """Converte configuração para dict."""
        return {
            "version": self.version,
            "server": asdict(self.server),
            "retry": asdict(self.retry),
            "circuit_breaker": asdict(self.circuit_breaker),
            "cache": asdict(self.cache),
            "projection": asdict(self.projection),
            "metrics": asdict(self.metrics),
            "debug": self.debug,
            "log_level": self.log_level,
        }
    
    def to_json(self, path: Union[str, Path]):
        """Salva configuração em JSON."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    def validate(self) -> list[str]:
        """
        Valida a configuração.
        
        Returns:
            Lista de erros encontrados (vazia se válido)
        """
        errors = []
        
        # Valida server
        if self.server.port <= 0 or self.server.port > 65535:
            errors.append(f"Porta inválida: {self.server.port}")
        
        # Valida retry
        if self.retry.max_retries < 0:
            errors.append("max_retries não pode ser negativo")
        
        # Valida cache
        if self.cache.backend not in ("memory", "redis", "sqlite"):
            errors.append(f"Backend de cache inválido: {self.cache.backend}")
        
        # Valida projection
        if self.projection.backend not in ("mock", "anthropic", "openai", "service"):
            errors.append(f"Backend de projeção inválido: {self.projection.backend}")
        
        if self.projection.backend == "anthropic" and not self.projection.anthropic_api_key:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                errors.append("API key da Anthropic necessária")
        
        return errors


def _merge_configs(base: LeetConfig, override: LeetConfig) -> LeetConfig:
    """
    Faz merge de duas configurações.
    
    Override tem prioridade sobre base para valores não-default.
    """
    def is_default(field_value, field_type):
        """Verifica se valor é default do dataclass."""
        if field_value is None:
            return True
        if field_type == bool and field_value == False:
            return True
        if field_type in (int, float) and field_value == 0:
            return True
        if field_type == str and field_value == "":
            return True
        if field_type == list and field_value == []:
            return True
        return False
    
    # Simples: retorna override se tiver valores não-default
    # Caso contrário retorna base
    result = LeetConfig()
    
    for field_name, field_def in LeetConfig.__dataclass_fields__.items():
        base_val = getattr(base, field_name)
        override_val = getattr(override, field_name)
        
        # Para dataclasses aninhados, faz merge recursivo
        if hasattr(base_val, '__dataclass_fields__'):
            merged = _merge_dataclasses(base_val, override_val)
            setattr(result, field_name, merged)
        else:
            # Usa override se não for default
            if not is_default(override_val, type(override_val)):
                setattr(result, field_name, override_val)
            else:
                setattr(result, field_name, base_val)
    
    return result


def _merge_dataclasses(base, override):
    """Faz merge de dois dataclasses."""
    result = base.__class__()
    
    for field_name in base.__dataclass_fields__:
        base_val = getattr(base, field_name)
        override_val = getattr(override, field_name)
        
        # Override tem prioridade se não for valor "vazio"
        if override_val is not None:
            if isinstance(override_val, (list, dict)) and len(override_val) == 0:
                setattr(result, field_name, base_val)
            else:
                setattr(result, field_name, override_val)
        else:
            setattr(result, field_name, base_val)
    
    return result


# Configuração global
_global_config: Optional[LeetConfig] = None


def get_config() -> LeetConfig:
    """Retorna configuração global."""
    global _global_config
    if _global_config is None:
        _global_config = LeetConfig.load()
    return _global_config


def set_config(config: LeetConfig):
    """Define configuração global."""
    global _global_config
    _global_config = config


def init_config(
    path: Optional[Union[str, Path]] = None,
    env_prefix: str = "LEET_",
    **overrides
) -> LeetConfig:
    """
    Inicializa configuração global.
    
    Args:
        path: Caminho do arquivo de configuração
        env_prefix: Prefixo para variáveis de ambiente
        **overrides: Valores para sobrescrever
        
    Returns:
        Configuração inicializada
    """
    global _global_config
    
    _global_config = LeetConfig.load(path=path, env_prefix=env_prefix)
    
    # Aplica overrides
    for key, value in overrides.items():
        if hasattr(_global_config, key):
            setattr(_global_config, key, value)
    
    return _global_config
