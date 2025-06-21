# Storage Adapters Guide

This application features a pluggable storage backend system, allowing you to choose where your item data is stored. This is managed through the `StorageInterface` and specific adapter implementations.

## The `StorageInterface`

Located in `src/core/storage_interface.py`, the `StorageInterface` is an abstract base class that defines the contract all storage adapters must adhere to. It includes methods for:

*   `create(item_data: dict) -> dict`: Create a single item.
*   `read_one(item_id: str) -> Optional[dict]`: Read a single item by its ID.
*   `read_all(filters, sort_by, offset, limit) -> PaginatedDbResponse`: Read items with filtering, sorting, and pagination.
*   `update(item_id: str, item_data: dict) -> Optional[dict]`: Update an existing item.
*   `delete(item_id: str) -> bool`: Delete an item.
*   `create_many(items_data: List[dict]) -> List[dict]`: Batch create multiple items.
*   `export_all() -> List[dict]`: Export all items (no pagination/filtering).

Developers can create new storage adapters by inheriting from this interface and implementing these methods.

## Selecting an Adapter

The active storage adapter is chosen in `config/config.ini` via the `ADAPTER_TYPE` setting in the `[DEFAULT]` section. See [`configuration.md`](configuration.md) for details.

## Available Adapters

Below are details for each built-in storage adapter.

### 1. MemoryStorage (`memory`)

*   **Source**: `src/adapters/memory_storage.py`
*   **How it works**: Stores all item data in a Python dictionary in the application's memory.
*   **Persistence**: None. Data is lost when the application stops or restarts.
*   **Use Cases**: Ideal for development, testing, or scenarios where data persistence is not required. It's the fastest adapter due to no I/O overhead.
*   **Configuration**: No specific configuration needed in `config.ini` beyond setting `ADAPTER_TYPE = memory`.
*   **Querying**: Filtering and sorting are performed in-memory on the full dataset after it's retrieved.

### 2. CsvStorage (`csv`)

*   **Source**: `src/adapters/csv_storage.py`
*   **How it works**: Persists item data to a CSV (Comma Separated Values) file. It maintains an in-memory cache (`_data_cache`) of the CSV content for reads and writes the entire cache back to the file upon modification.
*   **Configuration (`[csv]` section in `config.ini`):**
    *   `filepath`: Path to the CSV file (e.g., `data/items.csv`).
    *   `fieldnames`: Comma-separated list of headers (e.g., `id,name,description,data`).
*   **Data Serialization**: The `data` field (which is a dictionary in the Item model) is stored as a JSON string within its CSV cell. It's automatically serialized/deserialized by the adapter.
*   **Use Cases**: Simple file-based persistence, human-readable data file (though JSON strings can be long). Not recommended for very large datasets or high concurrency due to whole-file reads/writes for modifications.
*   **Querying**: Filtering and sorting are performed in-memory after loading all CSV data into the cache.

### 3. DatabaseStorage (`database` - SQLite)

*   **Source**: `src/adapters/database_storage.py`
*   **How it works**: Uses SQLAlchemy to interact with an SQLite database. Data is stored in a table typically named `items`.
*   **Configuration (`[database]` section in `config.ini`):**
    *   `db_url`: SQLAlchemy connection URL (e.g., `sqlite:///./data/app.db`).
*   **Schema**: See [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) for table structure. The table is auto-created if it doesn't exist.
*   **Use Cases**: Robust single-file database solution, good for development, testing, and small to medium applications where a full RDBMS server is not required. Supports ACID properties.
*   **Querying**: Filtering and sorting are translated directly into SQL queries by SQLAlchemy, making them efficient and performed at the database level.

### 4. MySQLStorage (`mysql`)

*   **Source**: `src/adapters/mysql_storage.py`
*   **How it works**: Uses SQLAlchemy and the `PyMySQL` driver to connect to a MySQL database server. Data is stored in a table typically named `items_mysql`.
*   **Configuration (`[mysql]` section in `config.ini`):**
    *   `db_url`: SQLAlchemy connection URL (e.g., `mysql+pymysql://user:pass@host:port/dbname`). The specified database must exist on the server.
*   **Schema**: See [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md). The table is auto-created within the specified database if it doesn't exist.
*   **Use Cases**: Production-grade relational database storage, suitable for larger applications requiring scalability, concurrency, and advanced database features.
*   **Querying**: Filtering and sorting are translated into efficient SQL queries by SQLAlchemy, performed at the database level.

### 5. RedisStorage (`redis`)

*   **Source**: `src/adapters/redis_storage.py`
*   **How it works**: Connects to a Redis server and stores each item as a JSON string under a unique key (e.g., `item:<uuid>`).
*   **Configuration (`[redis]` section in `config.ini`):**
    *   `redis_url`: Connection URL for Redis (e.g., `redis://localhost:6379/0`).
*   **Use Cases**: Fast key-value storage, often used for caching or session management. Can be used as a primary data store if data modeling fits key-value patterns and query needs are simple or handled by external indexing.
*   **Querying (Important Considerations)**:
    *   **`read_all` / `export_all`**: These methods use `KEYS item:*` to find all item keys, then `MGET` to fetch them. **`KEYS` can be very slow and block a production Redis server if there are many keys.** Use with extreme caution in production or ensure your Redis key space for items is manageable.
    *   **Filtering and Sorting**: Performed **in-memory** within the adapter after fetching all items (retrieved via `KEYS`). This is not efficient for large datasets in Redis.
    *   For advanced querying on Redis (beyond simple key lookups), consider building secondary indexes (e.g., using Redis sets, sorted sets, or Redisearch module), which are not implemented by default in this adapter.
*   **Batch Operations**: `create_many` uses Redis pipelines for efficient batch writes.

Choosing the right adapter depends on your project's requirements for persistence, scalability, performance, and operational complexity.
