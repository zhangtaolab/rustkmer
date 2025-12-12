"""
Thread safety utilities for RustKmer Python API.

This module provides thread-safe wrappers and synchronization primitives
for concurrent access to databases and other resources.

Important considerations for PyO3 bindings:
- Python's GIL is automatically managed for Python objects
- Rust operations that don't touch Python objects can release the GIL
- Use thread-safe wrappers for database operations to prevent race conditions
- Consider using connection pools for better concurrency
"""

import threading
import time
from typing import Any, Dict, Optional, Callable, TypeVar, Generic
from contextlib import contextmanager
from functools import wraps
import weakref

# Type variable for generic types
T = TypeVar('T')


class ThreadSafeDatabase:
    """
    Thread-safe wrapper for Database objects.

    Provides thread-safe access to database operations using Python's threading primitives.
    Since RustKmer's heavy operations are in Rust and may release the GIL,
    this wrapper ensures Python-level thread safety for consistent state.

    Note on GIL:
    - PyO3 automatically manages the GIL for Python object access
    - Heavy Rust operations (like queries, merges) should release the GIL internally
    - This wrapper primarily protects Python-level state and ensures operation atomicity
    """

    def __init__(self, database) -> None:
        """
        Initialize thread-safe wrapper.

        Args:
            database: Database instance to wrap
        """
        self._database = database
        # Use RLock to allow re-entrancy (same thread can acquire multiple times)
        self._lock = threading.RLock()
        # Track if database is currently being modified
        self._modified = threading.Event()
        self._modified.clear()

    def _validate_database_loaded(self) -> None:
        """Internal helper to validate database is loaded."""
        if not self._database._loaded:
            raise RuntimeError("No database loaded. Call load() first.")

    @contextmanager
    def _ensure_loaded(self) -> None:
        """Context manager to ensure database is loaded during operation."""
        self._validate_database_loaded()
        yield

    def query(self, kmer: str) -> Any:
        """
        Thread-safe query operation.

        Since this is a read-only operation, multiple threads can query simultaneously.
        The underlying Rust implementation should release the GIL during heavy computation.
        """
        with self._lock:
            with self._ensure_loaded():
                return self._database.query(kmer)

    def exists(self, kmer: str) -> bool:
        """Thread-safe existence check."""
        with self._lock:
            with self._ensure_loaded():
                return self._database.exists(kmer)

    def get_count(self, kmer: str) -> int:
        """Thread-safe count retrieval."""
        with self._lock:
            with self._ensure_loaded():
                return self._database.get_count(kmer)

    def get_stats(self, include_metadata: bool = True) -> Any:
        """Thread-safe statistics retrieval."""
        with self._lock:
            with self._ensure_loaded():
                return self._database.get_stats(include_metadata)

    def load(self, database_path) -> None:
        """
        Thread-safe database loading.

        This is an exclusive operation - other threads must wait for loading to complete.
        """
        with self._lock:
            # Set modified flag to indicate state change
            self._modified.set()
            try:
                result = self._database.load(database_path)
                return result
            finally:
                self._modified.clear()

    def dump(self, output_path, format: str = "text", **kwargs) -> None:
        """Thread-safe database dump."""
        with self._lock:
            with self._ensure_loaded():
                return self._database.dump(output_path, format, **kwargs)

    def reload(self, force_memory_mapping: Optional[bool] = None) -> None:
        """
        Thread-safe database reload.

        This is an exclusive operation - other threads must wait for reload to complete.
        """
        with self._lock:
            with self._ensure_loaded():
                # Set modified flag to indicate state change
                self._modified.set()
                try:
                    result = self._database.reload(force_memory_mapping)
                    return result
                finally:
                    self._modified.clear()

    def close(self) -> None:
        """Thread-safe database close."""
        with self._lock:
            return self._database.close()

    @property
    def kmer_size(self):
        """Thread-safe k-mer size access."""
        with self._lock:
            with self._ensure_loaded():
                return self._database.kmer_size

    @property
    def canonical(self):
        """Thread-safe canonical property access."""
        with self._lock:
            with self._ensure_loaded():
                return self._database.canonical

    @property
    def sorted(self):
        """Thread-safe sorted property access."""
        with self._lock:
            with self._ensure_loaded():
                return self._database.sorted

    @property
    def uses_memory_mapping(self):
        """Thread-safe memory mapping property access."""
        with self._lock:
            with self._ensure_loaded():
                return self._database.uses_memory_mapping

    def merge(self, other, output_path, strategy: str = "sum", **kwargs) -> Any:
        """
        Thread-safe merge operation.

        This is an exclusive operation - other threads must wait for merge to complete.
        """
        with self._lock:
            with self._ensure_loaded():
                # Set modified flag to indicate state change
                self._modified.set()
                try:
                    result = self._database.merge(other, output_path, strategy, **kwargs)
                    return result
                finally:
                    self._modified.clear()

    def __getattr__(self, name) -> Any:
        """Delegate attribute access to wrapped database."""
        return getattr(self._database, name)

    def wait_for_stable(self, timeout: Optional[float] = None) -> None:
        """
        Wait for database to be in a stable state (no modifications in progress).

        Args:
            timeout: Maximum time to wait (None for indefinite)
        """
        if timeout:
            self._modified.wait(timeout)
        else:
            self._modified.wait()


class ThreadSafeCache(Generic[T]):
    """
    Thread-safe LRU cache with TTL support.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[float] = None) -> None:
        """
        Initialize thread-safe cache.

        Args:
            max_size: Maximum number of items to cache
            ttl_seconds: Time-to-live for cache entries (None for no expiration)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._access_order = []

    def get(self, key: str) -> Optional[T]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check TTL
            if self.ttl_seconds and time.time() - entry['timestamp'] > self.ttl_seconds:
                del self._cache[key]
                self._access_order.remove(key)
                return None

            # Update access time
            entry['timestamp'] = time.time()
            self._access_order.remove(key)
            self._access_order.append(key)

            return entry['value']

    def put(self, key: str, value: T) -> None:
        """
        Put value into cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = self._access_order.pop(0)
                del self._cache[oldest_key]

            # Add or update entry
            self._cache[key] = {
                'value': value,
                'timestamp': time.time()
            }

            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


class ConnectionPool(Generic[T]):
    """
    Thread-safe pool of database connections.

    Manages a pool of database instances for concurrent access.
    """

    def __init__(self, create_connection: Callable[[], T], max_size: int = 10) -> None:
        """
        Initialize connection pool.

        Args:
            create_connection: Function to create new connections
            max_size: Maximum number of connections in pool
        """
        self.create_connection = create_connection
        self.max_size = max_size
        self._pool = []
        self._in_use = set()
        self._lock = threading.RLock()
        self._created_count = 0

    @contextmanager
    def get_connection(self, timeout: Optional[float] = None):
        """
        Get a connection from the pool.

        Args:
            timeout: Maximum time to wait for connection (None for no limit)

        Returns:
            Connection from pool
        """
        start_time = time.time()

        with self._lock:
            # Try to get available connection
            while self._pool and len(self._in_use) >= self.max_size:
                if timeout and time.time() - start_time > timeout:
                    raise RuntimeError("Timeout waiting for database connection")
                time.sleep(0.001)

            # Create new connection if needed
            if not self._pool and self._created_count < self.max_size:
                conn = self.create_connection()
                self._created_count += 1
            else:
                conn = self._pool.pop()

            self._in_use.add(id(conn))

        try:
            yield conn
        finally:
            with self._lock:
                self._in_use.discard(id(conn))
                self._pool.append(conn)

    def close_all(self) -> None:
        """Close all connections in pool."""
        with self._lock:
            for conn in self._pool:
                if hasattr(conn, 'close'):
                    conn.close()
            self._pool.clear()
            self._in_use.clear()
            self._created_count = 0


def thread_safe(max_concurrent: Optional[int] = None) -> Callable:
    """
    Decorator to make a function thread-safe.

    Args:
        max_concurrent: Maximum concurrent executions (None for unlimited)

    Returns:
        Decorated function
    """
    def decorator(func):
        lock = threading.RLock()
        semaphore = threading.Semaphore(max_concurrent) if max_concurrent else None

        @wraps(func)
        def wrapper(*args, **kwargs):
            if semaphore:
                semaphore.acquire()

            try:
                with lock:
                    return func(*args, **kwargs)
            finally:
                if semaphore:
                    semaphore.release()

        return wrapper
    return decorator


class AtomicCounter:
    """
    Thread-safe atomic counter.
    """

    def __init__(self, initial_value: int = 0) -> None:
        """
        Initialize atomic counter.

        Args:
            initial_value: Initial counter value
        """
        self._value = initial_value
        self._lock = threading.RLock()

    def increment(self, delta: int = 1) -> int:
        """
        Increment counter.

        Args:
            delta: Amount to increment by

        Returns:
            New counter value
        """
        with self._lock:
            self._value += delta
            return self._value

    def decrement(self, delta: int = 1) -> int:
        """
        Decrement counter.

        Args:
            delta: Amount to decrement by

        Returns:
            New counter value
        """
        with self._lock:
            self._value -= delta
            return self._value

    def get(self) -> int:
        """
        Get current counter value.

        Returns:
            Current counter value
        """
        with self._lock:
            return self._value

    def set(self, value: int) -> None:
        """
        Set counter value.

        Args:
            value: New counter value
        """
        with self._lock:
            self._value = value


class ThreadLocal(Generic[T]):
    """
    Thread-local storage wrapper.
    """

    def __init__(self, factory: Callable[[], T]) -> None:
        """
        Initialize thread-local storage.

        Args:
            factory: Function to create initial value for each thread
        """
        self._storage = threading.local()
        self._factory = factory

    def get(self) -> T:
        """
        Get value for current thread.

        Returns:
            Thread-local value
        """
        if not hasattr(self._storage, 'value'):
            self._storage.value = self._factory()
        return self._storage.value

    def set(self, value: T) -> None:
        """
        Set value for current thread.

        Args:
            value: Value to set
        """
        self._storage.value = value


# Global thread-local storage for default database connections
_default_connections = ThreadLocal(lambda: None)


def get_default_connection() -> Optional[Any]:
    """Get default database connection for current thread."""
    return _default_connections.get()


def set_default_connection(connection: Any) -> None:
    """Set default database connection for current thread."""
    _default_connections.set(connection)


@contextmanager
def default_connection_context(connection: Any) -> None:
    """
    Context manager for temporarily setting default connection.

    Args:
        connection: Connection to set as default
    """
    old_connection = get_default_connection()
    set_default_connection(connection)
    try:
        yield
    finally:
        set_default_connection(old_connection)


def make_thread_safe(database) -> ThreadSafeDatabase:
    """
    Create a thread-safe wrapper for a database instance.

    Args:
        database: Database instance to wrap

    Returns:
        ThreadSafeDatabase wrapper instance

    Example:
        >>> from rustkmer import Database
        >>> from rustkmer.thread_safety import make_thread_safe
        >>>
        >>> db = Database("data.rkdb")
        >>> safe_db = make_thread_safe(db)
        >>>
        >>> # Now safe_db can be safely used from multiple threads
        >>> # All operations are properly synchronized
    """
    return ThreadSafeDatabase(database)


def with_thread_safe(database_func) -> Callable:
    """
    Decorator to ensure database returned by function is thread-safe.

    Args:
        database_func: Function that returns a Database instance

    Returns:
        Decorated function that returns ThreadSafeDatabase

    Example:
        >>> from rustkmer import Database
        >>> from rustkmer.thread_safety import with_thread_safe
        >>>
        >>> @with_thread_safe
        >>> def load_database(path):
        >>>     return Database(path)
        >>>
        >>> db = load_database("data.rkdb")  # Returns ThreadSafeDatabase
    """
    @wraps(database_func)
    def wrapper(*args, **kwargs):
        database = database_func(*args, **kwargs)
        return make_thread_safe(database)
    return wrapper