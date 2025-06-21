# Flexible CRUD REST API

This project provides a flexible REST API for Create, Read, Update, and Delete (CRUD) operations, designed with an adaptable backend architecture. It supports various storage solutions like in-memory, CSV, SQLite, MySQL, and Redis.

**For comprehensive documentation, please see the `docs/` directory, starting with [`docs/index.md`](docs/index.md).**

## Overview

The API allows for managing generic "item" resources and features:
*   Standard CRUD operations.
*   Advanced querying with filtering and sorting.
*   Batch creation and data export.
*   Configurable storage backends.
*   Automatic interactive API documentation (Swagger UI & ReDoc).

## Quick Start

1.  **Clone & Setup**:
    ```bash
    git clone your_repository_url_placeholder # Replace with actual URL
    cd your_project_directory_placeholder
    ./run_dev_tasks.sh setup
    ```
    (See [`docs/getting_started.md`](docs/getting_started.md) for detailed setup).
2.  **Configure**: Edit `config/config.ini` to select and configure your desired storage adapter (e.g., `memory`, `csv`, `database`, `mysql`, `redis`).
    (See [`docs/configuration.md`](docs/configuration.md) for details).
3.  **Run**:
    ```bash
    # Ensure virtual environment from 'setup' is active
    python3 main.py
    ```
    API will be at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Documentation

**Full, detailed documentation can be found in the [`docs/`](docs/) directory.**

Key sections include:
*   [`docs/index.md`](docs/index.md): Introduction and navigation.
*   [`docs/getting_started.md`](docs/getting_started.md): Setup, configuration, running the app and tests.
*   [`docs/api_reference.md`](docs/api_reference.md): Detailed information on all API endpoints.
*   [`docs/query_language.md`](docs/query_language.md): Guide to advanced filtering and sorting.
*   [`docs/storage_adapters.md`](docs/storage_adapters.md): Details on each storage backend.
*   [`docs/configuration.md`](docs/configuration.md): In-depth guide to `config.ini`.
*   [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md): SQL database schema.
*   [`docs/development_guide.md`](docs/development_guide.md): Information for developers and contributors.

## Development

The `run_dev_tasks.sh` script helps with common development tasks:
*   `./run_dev_tasks.sh format`: Format code with Black.
*   `./run_dev_tasks.sh lint`: Lint with Flake8.
*   `./run_dev_tasks.sh test`: Run all unit tests.
*   `./run_dev_tasks.sh all`: Run format, lint, and test.
(See [`docs/development_guide.md`](docs/development_guide.md) for more details).

## Contributing

Contributions are welcome! Please refer to the [`docs/development_guide.md`](docs/development_guide.md) for coding conventions and guidelines.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details (if a LICENSE file exists).
