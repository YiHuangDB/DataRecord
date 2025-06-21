# Database Schema

This document outlines the database schema used by the SQL-based storage adapters (SQLite and MySQL).

## Table: `items` (Used by SQLite via `DatabaseStorage`)

This table stores the item data when using the SQLite backend.

| Column      | Type        | Constraints              | Description                                   |
|-------------|-------------|--------------------------|-----------------------------------------------|
| `id`        | `String(36)`| `PRIMARY KEY`, `INDEX`   | Unique identifier for the item (UUID4 hex).   |
| `name`      | `String(255)`| `NOT NULL`, `INDEX`      | Name of the item.                             |
| `description`| `Text`      | `NULLABLE`               | Optional descriptive text for the item.       |
| `data`      | `JSON`      |                          | Arbitrary key-value data associated with the item, stored as JSON. |

**Indexes:**
- Primary key index on `id`.
- Index on `name` (added to improve filter/sort performance).

## Table: `items_mysql` (Used by MySQL via `MySQLStorage`)

This table stores the item data when using the MySQL backend. It has an identical structure to the `items` table for SQLite to ensure consistency, though the underlying MySQL types might have slight variations from SQLite's interpretation of standard SQLAlchemy types.

| Column      | Type        | Constraints              | Description                                   |
|-------------|-------------|--------------------------|-----------------------------------------------|
| `id`        | `String(36)`| `PRIMARY KEY`, `INDEX`   | Unique identifier for the item (UUID4 hex).   |
| `name`      | `String(255)`| `NOT NULL`, `INDEX`      | Name of the item.                             |
| `description`| `Text`      | `NULLABLE`               | Optional descriptive text for the item.       |
| `data`      | `JSON`      |                          | Arbitrary key-value data associated with the item, stored as JSON. |

**Indexes:**
- Primary key index on `id`.
- Index on `name` (added to improve filter/sort performance).

## Initialization

The application uses SQLAlchemy's `metadata.create_all(engine)` method when a SQL-based storage adapter (SQLite or MySQL) is initialized. This command automatically creates the respective table (`items` or `items_mysql`) in the configured database if it does not already exist.

For MySQL, the database specified in the connection URL must exist beforehand. The application will create the table within that database.

No manual schema migration scripts (like Alembic) are used in the current version. Schema changes would require manual database adjustments or modifications to the SQLAlchemy models in the adapter code.
