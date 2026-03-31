"""
Sistema de cache persistente para o SDK 1337.

Suporta múltiplos backends:
- Memory: Cache em memória (LRU)
- SQLite: Cache persistente em arquivo
- Redis: Cache distribuído
- MongoDB: Cache em cluster MongoDB
"""

from __future__ import annotations

import hashlib
import json
import pickle
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from collections import OrderedDict


@dataclass
class CacheEntry:
    """Entrada do cache."""
    key: str
    value: Any
    created_at: float
    ttl_seconds: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    @property
    def is_expired(self) -> bool:
        """Verifica se entrada expirou."""
        return time.time() - self.created_at > self.ttl_seconds
    
    def touch(self):
        """Atualiza timestamp de acesso."""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheBackend(ABC):
    """Interface para backend de cache."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        """Define valor no cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove valor do cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Limpa todo o cache."""
        pass
    
    @abstractmethod
    def keys(self) -> list[str]:
        """Retorna todas as chaves."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Retorna número de entradas."""
        pass
    
    @abstractmethod
    def cleanup(self) -> int:
        """Remove entradas expiradas. Retorna número removido."""
        pass


class MemoryCache(CacheBackend):
    """Cache em memória com LRU eviction."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return None
            
            if entry.is_expired:
                del self._cache[key]
                return None
            
            entry.touch()
            # Move para o final (LRU)
            self._cache.move_to_end(key)
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            # Se já existe, atualiza
            if key in self._cache:
                entry = self._cache[key]
                entry.value = value
                entry.created_at = time.time()
                entry.ttl_seconds = ttl_seconds
                entry.touch()
                self._cache.move_to_end(key)
                return
            
            # Eviction se necessário
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl_seconds
            )
            self._cache[key] = entry
    
    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
    
    def keys(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())
    
    def size(self) -> int:
        with self._lock:
            return len(self._cache)
    
    def cleanup(self) -> int:
        with self._lock:
            expired = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired:
                del self._cache[key]
            return len(expired)


class SQLiteCache(CacheBackend):
    """Cache persistente em SQLite."""
    
    def __init__(self, db_path: str = ".leet_cache.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Inicializa schema do banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_seconds REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON cache(created_at)
            """)
            conn.commit()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT value, created_at, ttl_seconds FROM cache WHERE key = ?",
                    (key,)
                ).fetchone()
                
                if row is None:
                    return None
                
                value_blob, created_at, ttl_seconds = row
                
                # Verifica expiração
                if time.time() - created_at > ttl_seconds:
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                    conn.commit()
                    return None
                
                # Atualiza estatísticas
                conn.execute(
                    """UPDATE cache 
                       SET access_count = access_count + 1, 
                           last_accessed = ? 
                       WHERE key = ?""",
                    (time.time(), key)
                )
                conn.commit()
                
                return pickle.loads(value_blob)
    
    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            value_blob = pickle.dumps(value)
            created_at = time.time()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO cache 
                       (key, value, created_at, ttl_seconds, last_accessed)
                       VALUES (?, ?, ?, ?, ?)""",
                    (key, value_blob, created_at, ttl_seconds, created_at)
                )
                conn.commit()
    
    def delete(self, key: str) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
    
    def clear(self) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()
    
    def keys(self) -> list[str]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("SELECT key FROM cache").fetchall()
                return [row[0] for row in rows]
    
    def size(self) -> int:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
                return row[0] if row else 0
    
    def cleanup(self) -> int:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                now = time.time()
                cursor = conn.execute(
                    "DELETE FROM cache WHERE ? - created_at > ttl_seconds",
                    (now,)
                )
                conn.commit()
                return cursor.rowcount


class RedisCache(CacheBackend):
    """Cache usando Redis."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", key_prefix: str = "leet:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis = None
        self._connect()
    
    def _connect(self):
        """Conecta ao Redis."""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url)
        except ImportError:
            raise ImportError("redis não instalado. Instale: pip install redis")
    
    def _make_key(self, key: str) -> str:
        """Adiciona prefixo à chave."""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        if not self._redis:
            return None
        
        full_key = self._make_key(key)
        value = await self._redis.get(full_key)
        
        if value is None:
            return None
        
        return pickle.loads(value)
    
    async def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        if not self._redis:
            return
        
        full_key = self._make_key(key)
        value_blob = pickle.dumps(value)
        await self._redis.setex(full_key, int(ttl_seconds), value_blob)
    
    async def delete(self, key: str) -> None:
        if not self._redis:
            return
        
        full_key = self._make_key(key)
        await self._redis.delete(full_key)
    
    async def clear(self) -> None:
        if not self._redis:
            return
        
        # Deleta apenas chaves com nosso prefixo
        pattern = f"{self.key_prefix}*"
        cursor = 0
        
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break
    
    async def keys(self) -> list[str]:
        if not self._redis:
            return []
        
        pattern = f"{self.key_prefix}*"
        full_keys = await self._redis.keys(pattern)
        # Remove prefixo
        prefix_len = len(self.key_prefix)
        return [k.decode()[prefix_len:] if isinstance(k, bytes) else k[prefix_len:] 
                for k in full_keys]
    
    async def size(self) -> int:
        if not self._redis:
            return 0
        
        pattern = f"{self.key_prefix}*"
        count = 0
        cursor = 0
        
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
            count += len(keys)
            if cursor == 0:
                break
        
        return count
    
    async def cleanup(self) -> int:
        """Redis limpa automaticamente expirados."""
        return 0


class MongoCache(CacheBackend):
    """
    Cache usando MongoDB.
    
    Ideal para ambientes distribuídos com replicação
    e alta disponibilidade.
    
    Example:
        >>> cache = MongoCache(
        ...     uri="mongodb://localhost:27017",
        ...     db_name="leet_cache",
        ...     collection_name="projections"
        ... )
        >>> cache.set("key", value, ttl_seconds=3600)
    
    Schema do documento:
    {
        "_id": "cache:key",
        "key": "key",
        "value": <pickle bson binary>,
        "created_at": ISODate(),
        "expires_at": ISODate(),
        "access_count": 0,
        "last_accessed": ISODate(),
        "metadata": {}
    }
    """
    
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "leet_cache",
        collection_name: str = "cache",
        key_prefix: str = "leet:",
        max_pool_size: int = 50,
    ):
        """
        Args:
            uri: URI de conexão MongoDB
            db_name: Nome do database
            collection_name: Nome da collection
            key_prefix: Prefixo para chaves
            max_pool_size: Tamanho máximo do pool de conexões
        """
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.key_prefix = key_prefix
        self.max_pool_size = max_pool_size
        
        self._client = None
        self._collection = None
        self._lock = threading.RLock()
        
        self._connect()
        self._ensure_indexes()
    
    def _connect(self):
        """Conecta ao MongoDB."""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure
            
            self._client = MongoClient(
                self.uri,
                maxPoolSize=self.max_pool_size,
                serverSelectionTimeoutMS=5000,
            )
            
            # Verifica conexão
            self._client.admin.command('ping')
            
            self._collection = self._client[self.db_name][self.collection_name]
            
        except ImportError:
            raise ImportError(
                "pymongo não instalado. "
                "Instale: pip install pymongo"
            )
        except ConnectionFailure as e:
            raise ConnectionError(f"Não foi possível conectar ao MongoDB: {e}")
    
    def _ensure_indexes(self):
        """Cria índices necessários."""
        from pymongo import ASCENDING
        
        # Índice TTL para expiração automática
        self._collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
            background=True
        )
        
        # Índice para busca por chave
        self._collection.create_index(
            "key",
            unique=True,
            background=True
        )
        
        # Índice para last_accessed (para LRU)
        self._collection.create_index(
            "last_accessed",
            background=True
        )
    
    def _make_key(self, key: str) -> str:
        """Adiciona prefixo à chave."""
        return f"{self.key_prefix}{key}"
    
    def _to_document(self, key: str, value: Any, ttl_seconds: float) -> dict:
        """Converte entrada para documento MongoDB."""
        from bson.binary import Binary
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        
        return {
            "_id": self._make_key(key),
            "key": key,
            "value": Binary(pickle.dumps(value)),
            "created_at": now,
            "expires_at": now + timedelta(seconds=ttl_seconds),
            "access_count": 0,
            "last_accessed": now,
            "metadata": {}
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache."""
        with self._lock:
            if not self._collection:
                return None
            
            try:
                from datetime import datetime
                
                # Busca documento
                doc = self._collection.find_one({"_id": self._make_key(key)})
                
                if doc is None:
                    return None
                
                # Verifica expiração (o TTL do MongoDB deve fazer isso, mas verificamos também)
                if datetime.utcnow() > doc["expires_at"]:
                    self.delete(key)
                    return None
                
                # Atualiza estatísticas
                self._collection.update_one(
                    {"_id": self._make_key(key)},
                    {
                        "$inc": {"access_count": 1},
                        "$set": {"last_accessed": datetime.utcnow()}
                    }
                )
                
                return pickle.loads(doc["value"])
                
            except Exception as e:
                print(f"MongoDB get error: {e}")
                return None
    
    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        """Define valor no cache."""
        with self._lock:
            if not self._collection:
                return
            
            try:
                doc = self._to_document(key, value, ttl_seconds)
                
                # Upsert (insert ou update)
                self._collection.replace_one(
                    {"_id": doc["_id"]},
                    doc,
                    upsert=True
                )
                
            except Exception as e:
                print(f"MongoDB set error: {e}")
    
    def delete(self, key: str) -> None:
        """Remove valor do cache."""
        with self._lock:
            if not self._collection:
                return
            
            try:
                self._collection.delete_one({"_id": self._make_key(key)})
            except Exception as e:
                print(f"MongoDB delete error: {e}")
    
    def clear(self) -> None:
        """Limpa todo o cache (apenas chaves com prefixo)."""
        with self._lock:
            if not self._collection:
                return
            
            try:
                self._collection.delete_many(
                    {"_id": {"$regex": f"^{self.key_prefix}"}}
                )
            except Exception as e:
                print(f"MongoDB clear error: {e}")
    
    def keys(self) -> list[str]:
        """Retorna todas as chaves."""
        with self._lock:
            if not self._collection:
                return []
            
            try:
                cursor = self._collection.find(
                    {"_id": {"$regex": f"^{self.key_prefix}"}},
                    {"key": 1}
                )
                return [doc["key"] for doc in cursor]
            except Exception as e:
                print(f"MongoDB keys error: {e}")
                return []
    
    def size(self) -> int:
        """Retorna número de entradas."""
        with self._lock:
            if not self._collection:
                return 0
            
            try:
                return self._collection.count_documents(
                    {"_id": {"$regex": f"^{self.key_prefix}"}}
                )
            except Exception as e:
                print(f"MongoDB size error: {e}")
                return 0
    
    def cleanup(self) -> int:
        """Remove entradas expiradas (MongoDB TTL faz isso automaticamente)."""
        # O TTL do MongoDB já remove expirados
        # Mas podemos forçar uma limpeza se necessário
        return 0
    
    def get_stats(self) -> dict:
        """Retorna estatísticas da collection."""
        with self._lock:
            if not self._collection:
                return {}
            
            try:
                stats = self._collection.database.command("collStats", self.collection_name)
                return {
                    "document_count": stats.get("count", 0),
                    "size_bytes": stats.get("size", 0),
                    "avg_obj_size_bytes": stats.get("avgObjSize", 0),
                    "storage_size_bytes": stats.get("storageSize", 0),
                    "index_size_bytes": stats.get("totalIndexSize", 0),
                }
            except Exception as e:
                print(f"MongoDB stats error: {e}")
                return {}
    
    def close(self):
        """Fecha conexão com MongoDB."""
        if self._client:
            self._client.close()
            self._client = None
            self._collection = None


class Cache:
    """
    Cache unificado com múltiplos backends.
    
    Example:
        >>> # Cache em memória
        >>> cache = Cache(backend="memory", max_size=1000)
        >>> 
        >>> # Cache persistente
        >>> cache = Cache(backend="sqlite", path=".cache.db")
        >>> 
        >>> # Uso
        >>> cache.set("key", value, ttl_seconds=3600)
        >>> value = cache.get("key")
    """
    
    def __init__(
        self,
        backend: str = "memory",
        max_size: int = 10000,
        ttl_seconds: float = 3600.0,
        **backend_kwargs
    ):
        """
        Args:
            backend: 'memory', 'sqlite', 'redis'
            max_size: Tamanho máximo (para memory)
            ttl_seconds: TTL padrão
            **backend_kwargs: Argumentos específicos do backend
        """
        self.backend_type = backend
        self.default_ttl = ttl_seconds
        
        if backend == "memory":
            self._backend: CacheBackend = MemoryCache(max_size=max_size)
        elif backend == "sqlite":
            path = backend_kwargs.get("path", ".leet_cache.db")
            self._backend = SQLiteCache(db_path=path)
        elif backend == "redis":
            url = backend_kwargs.get("url", "redis://localhost:6379")
            prefix = backend_kwargs.get("key_prefix", "leet:")
            self._backend = RedisCache(redis_url=url, key_prefix=prefix)
        elif backend == "mongodb":
            uri = backend_kwargs.get("uri", "mongodb://localhost:27017")
            db = backend_kwargs.get("db_name", "leet_cache")
            coll = backend_kwargs.get("collection_name", "cache")
            prefix = backend_kwargs.get("key_prefix", "leet:")
            self._backend = MongoCache(
                uri=uri,
                db_name=db,
                collection_name=coll,
                key_prefix=prefix
            )
        else:
            raise ValueError(f"Backend não suportado: {backend}")
    
    def _make_key(self, *parts: str) -> str:
        """Cria chave a partir de partes."""
        combined = ":".join(parts)
        # Hash se muito longo
        if len(combined) > 200:
            return hashlib.sha256(combined.encode()).hexdigest()
        return combined
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache."""
        if hasattr(self._backend, 'get'):
            return self._backend.get(key)
        raise RuntimeError("Backend não suporta operação síncrona")
    
    async def aget(self, key: str) -> Optional[Any]:
        """Obtém valor do cache (async)."""
        if hasattr(self._backend, 'get'):
            import asyncio
            return await asyncio.get_event_loop().run_in_executor(
                None, self._backend.get, key
            )
        raise RuntimeError("Backend não suporta operação assíncrona")
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Define valor no cache."""
        ttl = ttl_seconds or self.default_ttl
        self._backend.set(key, value, ttl)
    
    async def aset(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Define valor no cache (async)."""
        import asyncio
        ttl = ttl_seconds or self.default_ttl
        await asyncio.get_event_loop().run_in_executor(
            None, self._backend.set, key, value, ttl
        )
    
    def delete(self, key: str) -> None:
        """Remove valor do cache."""
        self._backend.delete(key)
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        self._backend.clear()
    
    def keys(self) -> list[str]:
        """Retorna todas as chaves."""
        return self._backend.keys()
    
    def size(self) -> int:
        """Retorna número de entradas."""
        return self._backend.size()
    
    def cleanup(self) -> int:
        """Remove entradas expiradas."""
        return self._backend.cleanup()
    
    # Métodos utilitários para casos de uso comuns
    
    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: Optional[float] = None
    ) -> Any:
        """
        Obtém do cache ou computa se não existir.
        
        Example:
            >>> def expensive_computation():
            ...     return sum(range(1000000))
            >>> 
            >>> result = cache.get_or_compute("sum", expensive_computation)
        """
        value = self.get(key)
        if value is not None:
            return value
        
        value = compute_fn()
        self.set(key, value, ttl_seconds)
        return value
    
    async def aget_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: Optional[float] = None
    ) -> Any:
        """Async version de get_or_compute."""
        value = await self.aget(key)
        if value is not None:
            return value
        
        import asyncio
        if asyncio.iscoroutinefunction(compute_fn):
            value = await compute_fn()
        else:
            value = compute_fn()
        
        await self.aset(key, value, ttl_seconds)
        return value
    
    def get_projection(self, text: str) -> Optional[tuple[list[float], list[float]]]:
        """
        Obtém projeção do cache.
        
        Args:
            text: Texto projetado
            
        Returns:
            Tupla (sem, unc) ou None
        """
        key = self._make_key("proj", text)
        return self.get(key)
    
    def set_projection(
        self,
        text: str,
        sem: list[float],
        unc: list[float],
        ttl_seconds: Optional[float] = None
    ) -> None:
        """Armazena projeção no cache."""
        key = self._make_key("proj", text)
        self.set(key, (sem, unc), ttl_seconds)
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do cache."""
        return {
            "backend": self.backend_type,
            "size": self.size(),
            "default_ttl_seconds": self.default_ttl,
        }


# Cache global
_global_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Retorna cache global."""
    global _global_cache
    if _global_cache is None:
        _global_cache = Cache()
    return _global_cache


def set_cache(cache: Cache):
    """Define cache global."""
    global _global_cache
    _global_cache = cache
# Cache Backends
__all__ = [
    'CacheBackend',
    'MemoryCache', 
    'SQLiteCache',
    'RedisCache',
    'MongoCache',
    'Cache',
    'get_cache',
    'set_cache',
]
