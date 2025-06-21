# Getting Started

This guide will walk you through setting up the Flexible CRUD API project on your local machine, running the application, and executing tests.

## Prerequisites

*   **Python**: Version 3.7+ is recommended.
*   **Pip**: Python package installer (usually comes with Python).
*   **Git**: For cloning the repository.
*   **Bash-like shell**: For using the `run_dev_tasks.sh` script (common on Linux/macOS; Windows users can use WSL or Git Bash).
*   **(Optional) Backend Services**: If you plan to use MySQL or Redis, you'll need instances of these services running and accessible.

## 1. Clone the Repository

First, clone the project repository to your local machine. Replace `https://your-repository-url.com/project-name` with the actual repository URL and `your-project-directory` with the actual directory name.

```bash
git clone https://your-repository-url.com/project-name
cd your-project-directory
```

## 2. Set Up Virtual Environment & Install Dependencies

It's highly recommended to use a Python virtual environment to manage project dependencies. The `run_dev_tasks.sh` script can help automate this.

**Using the utility script (recommended):**
```bash
./run_dev_tasks.sh setup
```
This command will:
1.  Create a virtual environment named `venv` in the project root if it doesn't exist.
2.  Activate the virtual environment.
3.  Install all required dependencies from `requirements.txt` (core application) and `requirements-dev.txt` (development tools like linters).

**Manual Setup (if not using the script):**
```bash
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS and Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt # For development
```

## 3. Initial Configuration

The application's behavior, especially the storage backend, is controlled by `config/config.ini`.

1.  **Review `config/config.ini`**: Open this file in a text editor.
2.  **Choose a Storage Adapter**: In the `[DEFAULT]` section, set `ADAPTER_TYPE` to one of the supported values: `memory`, `csv`, `database` (for SQLite), `mysql`, or `redis`.
    ```ini
    [DEFAULT]
    ADAPTER_TYPE = memory
    ```
    For initial setup, `memory` or `csv` are the simplest as they don't require external services.
3.  **Configure Adapter-Specific Settings**: If you choose `csv`, `database`, `mysql`, or `redis`, ensure the corresponding section in `config.ini` has the correct parameters (e.g., file paths, database URLs). Refer to [`configuration.md`](configuration.md) for details.
    *   The `data/` directory will be used by default for CSV and SQLite files. Ensure your application has write permissions to this directory if using these adapters.

## 4. Running the Application

Once configured, you can run the API server:

```bash
# Ensure your virtual environment is active if you set it up manually:
# source venv/bin/activate (or venv\Scripts\activate on Windows)

# Run the main application
python3 main.py
```
(If you used `./run_dev_tasks.sh setup`, the script might leave the venv active, or you might need to activate it as shown above).

The application will start, typically on `http://localhost:8000`. You should see output indicating the server is running and which storage adapter is in use.

## 5. Accessing the API

*   **Base URL**: `http://localhost:8000`
*   **Interactive API Documentation (Swagger UI)**: `http://localhost:8000/docs`
    *   This interface allows you to explore all API endpoints, view their request/response models, and even try them out live.
*   **Alternative API Documentation (ReDoc)**: `http://localhost:8000/redoc`

## 6. Running Unit Tests

The project comes with a suite of unit tests to ensure functionality.

**Using the utility script (recommended):**
```bash
./run_dev_tasks.sh test
```
This command activates the virtual environment and then runs `python3 run_tests.py`.

**Manual Test Execution:**
```bash
# Ensure virtual environment is active
# source venv/bin/activate

python3 run_tests.py
```
*   **Database/Redis Tests**: Tests for MySQL and Redis adapters require respective services to be running and configured (via `TEST_MYSQL_URL` and `TEST_REDIS_URL` environment variables). If these services are unavailable or variables are not set, those specific tests will be skipped. See [`development_guide.md`](development_guide.md) for more on running tests.

You should now have the API running locally and know how to interact with it and verify its core functionality!
