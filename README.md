# Flexible CRUD REST API

## Description

This project provides a simple yet flexible REST API for Create, Read, Update, and Delete (CRUD) operations. Its key feature is the ability to dynamically configure different storage backends (In-Memory, CSV file, SQLite database, Redis, MySQL) without changing the core API logic. This is achieved through a configuration file and a storage adapter pattern.

The API is built using FastAPI, providing automatic interactive documentation (Swagger UI and ReDoc).

## Features

*   Standard CRUD operations for items.
*   Multiple backend support:
    *   **In-Memory:** Data is stored in memory and lost when the application stops.
    *   **CSV File:** Data is persisted in a CSV file.
    *   **SQLite Database:** Data is stored in a local SQLite database file.
    *   **Redis:** Data is stored in a Redis server.
    *   **MySQL:** Data is stored in a MySQL server.
*   Configuration via `config/config.ini` allows easy switching and setup of storage adapters.
*   FastAPI framework: High performance, easy to use, and provides automatic API documentation including request/response models.
*   Pagination for listing items.

## Project Structure

```
flexible-crud-api/
├── config/
│   └── config.ini      # Configuration file for storage adapter selection and settings
├── data/               # Default directory for CSV and SQLite files (content ignored by git)
├── src/
│   ├── adapters/       # Concrete implementations of storage backends (Memory, CSV, DB, Redis, MySQL)
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
    *   Set `ADAPTER_TYPE` in the `[DEFAULT]` section to one of `memory`, `csv`, `database`, `redis`, or `mysql`.

    #### In-Memory
    *   No specific configuration needed beyond setting `ADAPTER_TYPE = memory`.

    #### CSV File
    *   Set `ADAPTER_TYPE = csv`.
    *   Configure `filepath` (e.g., `data/items_config.csv`) and `fieldnames` (e.g., `id,name,description,data`) in the `[csv]` section.

    #### SQLite Database
    *   Set `ADAPTER_TYPE = database`.
    *   Configure `db_url` (e.g., `sqlite:///./data/items_config.db`) in the `[database]` section.

    #### Redis
    *   Set `ADAPTER_TYPE = redis`.
    *   Configure `redis_url` (e.g., `redis://localhost:6379/0`) in the `[redis]` section. Ensure your Redis server is running and accessible.

    #### MySQL
    *   Set `ADAPTER_TYPE = mysql`.
    *   Configure the `[mysql]` section:
        *   `db_url`: The SQLAlchemy connection string for MySQL. Format: `mysql+pymysql://USER:PASSWORD@HOST:PORT/DATABASE_NAME`.
          Example: `db_url = mysql+pymysql://myuser:mypass@localhost:3306/mydb`
    *   Ensure the specified database (`DATABASE_NAME`) already exists on your MySQL server. The application will create the necessary tables but not the database itself.
    *   The `PyMySQL` driver is included in `requirements.txt`.

3.  The `data/` directory is automatically created if it doesn't exist when using `csv` or `database` (SQLite) adapters with default paths pointing to this directory. Ensure the application has write permissions if necessary.

## Running the Application

1.  Ensure your chosen storage backend is correctly configured in `config/config.ini`.
2.  If using Redis or MySQL, make sure your respective server is running and accessible.
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
2.  **Service-Specific Tests:**
    *   **Redis Tests:** The tests for `RedisStorage` (`tests/adapters/test_redis_storage.py`) require a running Redis instance.
        *   By default, they attempt to connect to `redis://localhost:6379/9` (database 9).
        *   You can specify a different Redis URL for tests by setting the `TEST_REDIS_URL` environment variable.
        *   If the Redis server is not available or the specified database cannot be accessed, the Redis tests will be skipped automatically.
        *   **Caution:** The Redis tests will run `FLUSHDB` on the specified test database. Do not point it to a Redis database containing important data.
    *   **MySQL Tests:** For MySQL adapter tests (`tests/adapters/test_mysql_storage.py`), ensure a MySQL server is running and accessible. Set the `TEST_MYSQL_URL` environment variable to your MySQL test database connection string (e.g., `export TEST_MYSQL_URL="mysql+pymysql://user:pass@host:port/test_db"`). The tests will attempt to create and drop tables within this database. Tests will be skipped if this variable is not set or the database is unreachable.

## API Endpoints

The API provides the following endpoints for managing items. Each item typically consists of an `id`, `name`, `description`, and a flexible `data` field (dictionary).

*   `POST /items`: Create a new item.
*   `GET /items`: Retrieves a list of items. Supports pagination via `offset` and `limit` query parameters.
    *   Query Parameters:
        *   `offset` (integer, optional, default: 0): Number of items to skip.
        *   `limit` (integer, optional, default: 10, max: 100): Maximum number of items to return.
    *   Response: A JSON object containing `items` (list of item objects), `total_count` (total number of items available), `offset` (applied offset), and `limit` (applied limit).
*   `GET /items/{item_id}`: Retrieve a specific item by its unique ID.
*   `PUT /items/{item_id}`: Update an existing item by its ID.
*   `DELETE /items/{item_id}`: Delete an item by its ID.

For detailed request/response schemas and to try out the API, please visit the interactive documentation at `http://localhost:8000/docs`.

### Batch Operations

- `POST /items/batch`: Creates multiple items in a single request.
  - **Request Body**: A JSON array of item objects. Each object should match the structure for creating a single item (e.g., `name`, `description`, `data`). The `id` field is optional; if not provided, it will be generated by the server.
    ```json
    [
      {
        "name": "Batch Item 1",
        "description": "Description for batch item 1",
        "data": {"key1": "value1"}
      },
      {
        "name": "Batch Item 2",
        "data": {"key2": "value2"}
      }
    ]
    ```
  - **Response Body**: A JSON array of the created item objects, each including its server-assigned `id`.
    ```json
    [
      {
        "id": "generated-id-1",
        "name": "Batch Item 1",
        "description": "Description for batch item 1",
        "data": {"key1": "value1"}
      },
      {
        "id": "generated-id-2",
        "name": "Batch Item 2",
        "data": {"key2": "value2"}
      }
    ]
    ```

- `GET /items/export`: Exports all items currently in the storage.
  - **Request Body**: None.
  - **Response Body**: A JSON array of all item objects.
    ```json
    [
      {
        "id": "some-id-1",
        "name": "First Item",
        "description": "Details about first item",
        "data": {}
      },
      {
        "id": "some-id-2",
        "name": "Second Item",
        "description": "Details about second item",
        "data": {}
      }
      // ... all other items
    ]
    ```

## Extending

To add a new storage adapter:
1.  Create a new class in `src/adapters/` that inherits from `src.core.storage_interface.StorageInterface`.
2.  Implement all the abstract methods defined in `StorageInterface`, including the paginated `read_all` method.
3.  Add the new adapter type and its configuration options to `src/core/config.py` (in `get_storage_adapter`) and to `config/config.ini`.
4.  (Recommended) Add unit tests for your new adapter in `tests/adapters/`.
