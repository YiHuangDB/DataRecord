# Configuration Guide

The application's behavior, particularly the storage backend, is primarily controlled by the `config/config.ini` file. This guide details the structure and parameters of this configuration file.

## Overview

The `config.ini` file uses the INI file format, organized into sections (e.g., `[DEFAULT]`, `[csv]`).

## `[DEFAULT]` Section

This section contains global settings for the application.

*   **`ADAPTER_TYPE`**:
    *   **Description**: Specifies which storage adapter the application should use. This is the most crucial setting for determining the backend data store.
    *   **Valid Values**:
        *   `memory`: Uses the in-memory dictionary storage (data is lost when the application stops). Ideal for quick testing or development.
        *   `csv`: Uses a CSV file for data persistence.
        *   `database`: Uses an SQLite database file.
        *   `mysql`: Uses a MySQL database server.
        *   `redis`: Uses a Redis server for data storage.
    *   **Example**: `ADAPTER_TYPE = memory`

## Adapter-Specific Sections

Each storage adapter type (other than `memory`, which requires no specific configuration) has its own section for parameters.

### `[csv]` Section

Configuration for the CSV file storage adapter.

*   **`filepath`**:
    *   **Description**: The path to the CSV file where data will be stored. If the file doesn't exist, it will be created.
    *   **Default (if not specified or relative path)**: Typically created in the `data/` directory within the project root (e.g., `data/items.csv` or `data/items_config.csv` as seen in examples).
    *   **Example**: `filepath = data/my_items.csv`
*   **`fieldnames`**:
    *   **Description**: A comma-separated list of column headers for the CSV file. This must include `id`, `name`, `description`, and `data` to match the core item model.
    *   **Example**: `fieldnames = id,name,description,data`

### `[database]` Section (SQLite)

Configuration for the SQLite database storage adapter.

*   **`db_url`**:
    *   **Description**: The SQLAlchemy connection URL for the SQLite database. For a file-based SQLite database, this typically specifies the path to the database file.
    *   **Format**: `sqlite:///./path/to/your_database_file.db`
        *   `sqlite:///`: Indicates SQLite.
        *   `./`: Relative path from the project root. You can also use absolute paths.
    *   **Default (if relative path)**: Typically created in the `data/` directory (e.g., `data/items.db` or `data/items_config.db`).
    *   **Example**: `db_url = sqlite:///./data/main_app.db`

### `[mysql]` Section

Configuration for the MySQL database storage adapter.

*   **`db_url`**:
    *   **Description**: The SQLAlchemy connection URL for your MySQL database server.
    *   **Format**: `mysql+pymysql://USER:PASSWORD@HOST:PORT/DATABASE_NAME`
        *   `mysql+pymysql://`: Specifies MySQL with the PyMySQL driver.
        *   `USER`: Your MySQL username.
        *   `PASSWORD`: Your MySQL password.
        *   `HOST`: The hostname or IP address of your MySQL server (e.g., `localhost`).
        *   `PORT`: The port number MySQL is running on (default is `3306`).
        *   `DATABASE_NAME`: The name of the database to connect to. **This database must already exist on the server.** The application will create tables within this database but not the database itself.
    *   **Example**: `db_url = mysql+pymysql://app_user:app_pass@localhost:3306/app_db`

### `[redis]` Section

Configuration for the Redis storage adapter.

*   **`redis_url`**:
    *   **Description**: The connection URL for your Redis server.
    *   **Format**: `redis://HOST:PORT/DB_NUMBER`
        *   `HOST`: Hostname or IP address of the Redis server (e.g., `localhost`).
        *   `PORT`: Port Redis is running on (default is `6379`).
        *   `DB_NUMBER`: The Redis database number to use (e.g., `0`).
    *   **Example**: `redis_url = redis://localhost:6379/0`

## Notes

*   Ensure that paths specified for CSV or SQLite files are writable by the application.
*   For MySQL and Redis, ensure the respective database servers are running and accessible from where the application is hosted, and that credentials/connection details are correct.
