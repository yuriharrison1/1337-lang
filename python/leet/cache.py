"""
Persistent cache system for the 1337 SDK.

Supports multiple backends:
- Memory: In-memory cache (LRU)
- SQLite: File-based persistent cache
- Redis: Distributed cache
- MongoDB: Cache in a MongoDB cluster
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
from typing import Optional, Any, Callable, Union
from collections import OrderedDict


@dataclass
class CacheEntry:
    """Cache entry."""
    key: str
    value: Any
    created_at: float
    ttl_seconds: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Checks whether the entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds

    def touch(self):
        """Updates the access timestamp."""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheBackend(ABC):
    """Interface for a cache backend."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Gets a value from the cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        """Sets a value in the cache."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Removes a value from the cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clears the entire cache."""
        pass

    @abstractmethod
    def keys(self) -> list[str]:
        """Returns all keys."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Returns the number of entries."""
        pass

    @abstractmethod
    def cleanup(self) -> int:
        """Removes expired entries. Returns the number removed."""
        pass


class AsyncCacheBackend(ABC):
    """Interface for asynchronous backends (e.g. Redis)."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: float) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def clear(self) -> None: ...

    @abstractmethod
    async def keys(self) -> list[str]: ...

    @abstractmethod
    async def size(self) -> int: ...

    @abstractmethod
    async def cleanup(self) -> int: ...


class MemoryCache(CacheBackend):
    """In-memory cache with LRU eviction."""

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
            # Move to the end (LRU)
            self._cache.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            # If it already exists, update it
            if key in self._cache:
                entry = self._cache[key]
                entry.value = value
                entry.created_at = time.time()
                entry.ttl_seconds = ttl_seconds
                entry.touch()
                self._cache.move_to_end(key)
                return

            # Eviction if needed
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
    """Persistent SQLite cache."""

    def __init__(self, db_path: str = ".leet_cache.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initializes the database schema."""
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

                # Check expiration
                if time.time() - created_at > ttl_seconds:
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                    conn.commit()
                    return None

                # Update statistics
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


class RedisCache(AsyncCacheBackend):
    """Cache using Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379", key_prefix: str = "leet:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis = None
        self._connect()

    def _connect(self):
        """Connects to Redis."""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url)
        except ImportError:
            raise ImportError("redis not installed. Install with: pip install redis")

    def _make_key(self, key: str) -> str:
        """Adds a prefix to the key."""
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

        # Delete only keys with our prefix
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
        # Strip prefix
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
        """Redis automatically cleans up expired entries."""
        return 0


class MongoCache(CacheBackend):
    """
    Cache using MongoDB.

    Ideal for distributed environments with replication
    and high availability.

    Example:
        >>> cache = MongoCache(
        ...     uri="mongodb://localhost:27017",
        ...     db_name="leet_cache",
        ...     collection_name="projections"
        ... )
        >>> cache.set("key", value, ttl_seconds=3600)

    Document schema:
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
            uri: MongoDB connection URI
            db_name: Database name
            collection_name: Collection name
            key_prefix: Prefix for keys
            max_pool_size: Maximum connection pool size
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
        """Connects to MongoDB."""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure

            self._client = MongoClient(
                self.uri,
                maxPoolSize=self.max_pool_size,
                serverSelectionTimeoutMS=5000,
            )

            # Check connection
            self._client.admin.command('ping')

            self._collection = self._client[self.db_name][self.collection_name]

        except ImportError:
            raise ImportError(
                "pymongo not installed. "
                "Install with: pip install pymongo"
            )
        except ConnectionFailure as e:
            raise ConnectionError(f"Could not connect to MongoDB: {e}")

    def _ensure_indexes(self):
        """Creates the required indexes."""
        from pymongo import ASCENDING

        # TTL index for automatic expiration
        self._collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
            background=True
        )

        # Index for key lookup
        self._collection.create_index(
            "key",
            unique=True,
            background=True
        )

        # Index for last_accessed (for LRU)
        self._collection.create_index(
            "last_accessed",
            background=True
        )

    def _make_key(self, key: str) -> str:
        """Adds a prefix to the key."""
        return f"{self.key_prefix}{key}"

    def _to_document(self, key: str, value: Any, ttl_seconds: float) -> dict:
        """Converts an entry into a MongoDB document."""
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
        """Gets a value from the cache."""
        with self._lock:
            if not self._collection:
                return None

            try:
                from datetime import datetime

                # Look up document
                doc = self._collection.find_one({"_id": self._make_key(key)})

                if doc is None:
                    return None

                # Check expiration (MongoDB's TTL should handle this, but we check anyway)
                if datetime.utcnow() > doc["expires_at"]:
                    self.delete(key)
                    return None

                # Update statistics
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
        """Sets a value in the cache."""
        with self._lock:
            if not self._collection:
                return

            try:
                doc = self._to_document(key, value, ttl_seconds)

                # Upsert (insert or update)
                self._collection.replace_one(
                    {"_id": doc["_id"]},
                    doc,
                    upsert=True
                )

            except Exception as e:
                print(f"MongoDB set error: {e}")

    def delete(self, key: str) -> None:
        """Removes a value from the cache."""
        with self._lock:
            if not self._collection:
                return

            try:
                self._collection.delete_one({"_id": self._make_key(key)})
            except Exception as e:
                print(f"MongoDB delete error: {e}")

    def clear(self) -> None:
        """Clears the entire cache (only keys with our prefix)."""
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
        """Returns all keys."""
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
        """Returns the number of entries."""
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
        """Removes expired entries (MongoDB TTL does this automatically)."""
        # MongoDB's TTL already removes expired entries
        # But we can force a cleanup if needed
        return 0

    def get_stats(self) -> dict:
        """Returns statistics for the collection."""
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
        """Closes the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._collection = None


class Cache:
    """
    Unified cache with multiple backends.

    Supports synchronous backends (memory, sqlite) and asynchronous ones (redis).

    Example:
        >>> # In-memory cache
        >>> cache = Cache(backend="memory", max_size=1000)
        >>>
        >>> # Persistent cache
        >>> cache = Cache(backend="sqlite", path=".cache.db")
        >>>
        >>> # Synchronous usage
        >>> cache.set("key", value, ttl_seconds=3600)
        >>> value = cache.get("key")
        >>>
        >>> # Asynchronous usage (with Redis)
        >>> await cache.aset("key", value)
        >>> value = await cache.aget("key")
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
            backend: 'memory', 'sqlite', 'redis', 'mongodb'
            max_size: Maximum size (for memory)
            ttl_seconds: Default TTL
            **backend_kwargs: Backend-specific arguments
        """
        self.backend_type = backend
        self.default_ttl = ttl_seconds
        self._backend: Union[CacheBackend, AsyncCacheBackend]
        self._is_async = False

        if backend == "memory":
            self._backend = MemoryCache(max_size=max_size)
        elif backend == "sqlite":
            path = backend_kwargs.get("path", ".leet_cache.db")
            self._backend = SQLiteCache(db_path=path)
        elif backend == "redis":
            url = backend_kwargs.get("url", "redis://localhost:6379")
            prefix = backend_kwargs.get("key_prefix", "leet:")
            self._backend = RedisCache(redis_url=url, key_prefix=prefix)
            self._is_async = True
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
            raise ValueError(f"Unsupported backend: {backend}")

    def _make_key(self, *parts: str) -> str:
        """Builds a key from parts."""
        combined = ":".join(parts)
        # Hash if too long
        if len(combined) > 200:
            return hashlib.sha256(combined.encode()).hexdigest()
        return combined

    def _run_async(self, coro) -> Any:
        """Runs an async coroutine synchronously on a dedicated thread.

        Using a dedicated thread avoids conflicting with any event loop
        already running (e.g. FastAPI, Jupyter), since asyncio.run()
        creates a fresh loop on that thread.
        """
        import asyncio
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    def get(self, key: str) -> Optional[Any]:
        """Gets a value from the cache (synchronous)."""
        if self._is_async:
            return self._run_async(self._backend.get(key))
        return self._backend.get(key)

    async def aget(self, key: str) -> Optional[Any]:
        """Gets a value from the cache (async)."""
        if self._is_async:
            return await self._backend.get(key)
        # Synchronous backend - run in executor
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._backend.get, key
        )

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Sets a value in the cache (synchronous)."""
        ttl = ttl_seconds or self.default_ttl
        if self._is_async:
            self._run_async(self._backend.set(key, value, ttl))
        else:
            self._backend.set(key, value, ttl)

    async def aset(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Sets a value in the cache (async)."""
        ttl = ttl_seconds or self.default_ttl
        if self._is_async:
            await self._backend.set(key, value, ttl)
        else:
            import asyncio
            await asyncio.get_event_loop().run_in_executor(
                None, self._backend.set, key, value, ttl
            )

    def delete(self, key: str) -> None:
        """Removes a value from the cache (synchronous)."""
        if self._is_async:
            self._run_async(self._backend.delete(key))
        else:
            self._backend.delete(key)

    async def adelete(self, key: str) -> None:
        """Removes a value from the cache (async)."""
        if self._is_async:
            await self._backend.delete(key)
        else:
            import asyncio
            await asyncio.get_event_loop().run_in_executor(
                None, self._backend.delete, key
            )

    def clear(self) -> None:
        """Clears the entire cache (synchronous)."""
        if self._is_async:
            self._run_async(self._backend.clear())
        else:
            self._backend.clear()

    async def aclear(self) -> None:
        """Clears the entire cache (async)."""
        if self._is_async:
            await self._backend.clear()
        else:
            import asyncio
            await asyncio.get_event_loop().run_in_executor(
                None, self._backend.clear
            )

    def keys(self) -> list[str]:
        """Returns all keys (synchronous)."""
        if self._is_async:
            return self._run_async(self._backend.keys())
        return self._backend.keys()

    async def akeys(self) -> list[str]:
        """Returns all keys (async)."""
        if self._is_async:
            return await self._backend.keys()
        else:
            import asyncio
            return await asyncio.get_event_loop().run_in_executor(
                None, self._backend.keys
            )

    def size(self) -> int:
        """Returns the number of entries (synchronous)."""
        if self._is_async:
            return self._run_async(self._backend.size())
        return self._backend.size()

    async def asize(self) -> int:
        """Returns the number of entries (async)."""
        if self._is_async:
            return await self._backend.size()
        else:
            import asyncio
            return await asyncio.get_event_loop().run_in_executor(
                None, self._backend.size
            )

    def cleanup(self) -> int:
        """Removes expired entries (synchronous)."""
        if self._is_async:
            return self._run_async(self._backend.cleanup())
        return self._backend.cleanup()

    async def acleanup(self) -> int:
        """Removes expired entries (async)."""
        if self._is_async:
            return await self._backend.cleanup()
        else:
            import asyncio
            return await asyncio.get_event_loop().run_in_executor(
                None, self._backend.cleanup
            )

    # Utility methods for common use cases

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: Optional[float] = None
    ) -> Any:
        """
        Gets from the cache, or computes if it doesn't exist.

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
        """Async version of get_or_compute."""
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
        Gets a projection from the cache.

        Args:
            text: Projected text

        Returns:
            Tuple (sem, unc) or None
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
        """Stores a projection in the cache."""
        key = self._make_key("proj", text)
        self.set(key, (sem, unc), ttl_seconds)

    def get_stats(self) -> dict:
        """Returns cache statistics."""
        return {
            "backend": self.backend_type,
            "size": self.size(),
            "default_ttl_seconds": self.default_ttl,
        }


# Global cache
_global_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Returns the global cache."""
    global _global_cache
    if _global_cache is None:
        _global_cache = Cache()
    return _global_cache


def set_cache(cache: Cache):
    """Sets the global cache."""
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
