# Flexible CRUD REST API

## Description

This project provides a simple yet flexible REST API for Create, Read, Update, and Delete (CRUD) operations. Its key feature is the ability to dynamically configure different storage backends (In-Memory, CSV file, SQLite database, Redis) without changing the core API logic. This is achieved through a configuration file and a storage adapter pattern.

The API is built using FastAPI, providing automatic interactive documentation (Swagger UI and ReDoc).

## Features

*   Standard CRUD operations for items.
*   Multiple backend support:
    *   **In-Memory:** Data is stored in memory and lost when the application stops.
    *   **CSV File:** Data is persisted in a CSV file.
    *   **SQLite Database:** Data is stored in a local SQLite database file.
    *   **Redis:** Data is stored in a Redis server.
*   Configuration via `config/config.ini` allows easy switching and setup of storage adapters.
*   FastAPI framework: High performance, easy to use, and provides automatic API documentation.
*   Asynchronous support for all storage operations.

## Project Structure

```
flexible-crud-api/
├── config/
│   └── config.ini      # Configuration file for storage adapter selection and settings
├── data/               # Default directory for CSV and SQLite files (content ignored by git)
├── src/
│   ├── adapters/       # Concrete implementations of storage backends (Memory, CSV, DB, Redis)
│   ├── api/            # FastAPI application logic, routes, and request/response models
│   ├── core/           # Core components: Pydantic models, StorageInterface, configuration loader
│   └── __init__.py
├── tests/              # Unit and integration tests
│   ├── adapters/       # Tests for each storage adapter
│   ├── api/            # Tests for the API endpoints
│   └── __init__.py
├── .gitignore          # Specifies intentionally untracked files that Git should ignore
├── main.py             # Main application entry point to run the FastAPI server
├── requirements.txt    # Python dependencies for the project
├── run_tests.py        # Script to discover and execute unit tests
└── README.md           # This file
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd flexible-crud-api
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```
    *   On macOS/Linux: `source venv/bin/activate`
    *   On Windows: `venv\Scripts\activate`

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  The primary configuration file is `config/config.ini`.
2.  Edit `config/config.ini` to select and configure the desired storage backend:
    *   Set `ADAPTER_TYPE` in the `[DEFAULT]` section to one of `memory`, `csv`, `database`, or `redis`.
    *   **For `csv`:**
        *   Configure `filepath` (e.g., `data/items_config.csv`) and `fieldnames` (e.g., `id,name,description,data`) in the `[csv]` section.
    *   **For `database` (SQLite):**
        *   Configure `db_url` (e.g., `sqlite:///./data/items_config.db`) in the `[database]` section.
    *   **For `redis`:**
        *   Configure `redis_url` (e.g., `redis://localhost:6379/0`) in the `[redis]` section. Ensure your Redis server is running and accessible at this URL.
3.  The `data/` directory is automatically created if it doesn't exist when using `csv` or `database` adapters with default paths pointing to this directory. Ensure the application has write permissions if necessary.

## Running the Application

1.  Ensure your chosen storage backend is correctly configured in `config/config.ini`.
2.  If using Redis, make sure your Redis server is running.
3.  Run the FastAPI application:
    ```bash
    python main.py
    ```
4.  The API will be available at `http://localhost:8000`.
    *   Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
    *   Alternative API documentation (ReDoc): `http://localhost:8000/redoc`

## Running Tests

1.  To run all unit tests:
    ```bash
    python run_tests.py
    ```
2.  **Redis Tests:** The tests for `RedisStorage` (`tests/adapters/test_redis_storage.py`) require a running Redis instance.
    *   By default, they attempt to connect to `redis://localhost:6379/9` (database 9).
    *   You can specify a different Redis URL for tests by setting the `TEST_REDIS_URL` environment variable.
    *   If the Redis server is not available or the specified database cannot be accessed, the Redis tests will be skipped automatically.
    *   **Caution:** The Redis tests will run `FLUSHDB` on the specified test database. Do not point it to a Redis database containing important data.

## API Endpoints

The API provides the following endpoints for managing items. Each item typically consists of an `id`, `name`, `description`, and a flexible `data` field (dictionary).

*   `POST /items`: Create a new item.
*   `GET /items`: Retrieve a list of all items.
*   `GET /items/{item_id}`: Retrieve a specific item by its ID.
*   `PUT /items/{item_id}`: Update an existing item by its ID.
*   `DELETE /items/{item_id}`: Delete an item by its ID.

For detailed request/response schemas and to try out the API, please visit the interactive documentation at `http://localhost:8000/docs`.

## Extending

To add a new storage adapter:
1.  Create a new class in `src/adapters/` that inherits from `src.core.storage_interface.StorageInterface`.
2.  Implement all the abstract methods defined in `StorageInterface`.
3.  Add the new adapter type and its configuration options to `src/core/config.py` (in `get_storage_adapter`) and to `config/config.ini`.
4.  (Recommended) Add unit tests for your new adapter in `tests/adapters/`.
