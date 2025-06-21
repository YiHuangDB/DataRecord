# Welcome to the Flexible CRUD API Documentation

## Introduction

This project provides a flexible REST API for Create, Read, Update, and Delete (CRUD) operations on a generic "item" resource. Its core strength lies in its adaptable backend architecture, allowing you to easily switch between different data storage solutions like in-memory dictionaries, CSV files, SQLite, MySQL, or Redis, all configured through a simple INI file.

This documentation serves as a comprehensive guide for both users interacting with the API and developers looking to understand, extend, or contribute to the project.

## Core Features

*   **Simple RESTful Interface**: Standard HTTP methods for CRUD operations on items.
*   **Adaptable Backend**: Supports multiple storage types:
    *   In-Memory (for testing/development)
    *   CSV File
    *   SQLite (via DatabaseStorage)
    *   MySQL
    *   Redis
*   **Configuration Driven**: Easily select and configure storage adapters via `config/config.ini`.
*   **Advanced Querying**: Filter by various field operators, sort results, and paginate through large datasets.
*   **Batch Operations**: Efficiently create multiple items or export all data.
*   **Automatic API Docs**: Interactive API documentation available via Swagger UI (`/docs`) and ReDoc (`/redoc`) thanks to FastAPI.
*   **Developer Friendly**: Includes unit tests and a utility script (`run_dev_tasks.sh`) for common development tasks like linting, formatting, and testing.

## Navigating This Documentation

*   **Getting Started**: If you're new, start here to set up and run the project.
    *   [`getting_started.md`](getting_started.md)
*   **Configuration**: Detailed guide on `config.ini` and adapter settings.
    *   [`configuration.md`](configuration.md)
*   **API Reference**: In-depth look at all API endpoints, request/response formats, and examples.
    *   [`api_reference.md`](api_reference.md)
*   **Advanced Querying**: Master the powerful filtering and sorting syntax.
    *   [`query_language.md`](query_language.md)
*   **Storage Adapters**: Understand the different backends and their specifics.
    *   [`storage_adapters.md`](storage_adapters.md)
*   **Database Schema**: Details on the SQL table structures.
    *   [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md)
*   **Development Guide**: For contributors and those looking to extend the project.
    *   [`development_guide.md`](development_guide.md)

## Project Repository

For the source code, issue tracking, and contributions, please visit the [Project Repository](https://your-repository-url.com/project-name).
