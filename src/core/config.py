"""
Handles loading application configuration and initializing the appropriate storage adapter.

This module reads settings from a 'config.ini' file to determine which storage backend
(e.g., memory, CSV, database, Redis, MySQL) to use and what its specific parameters are.
"""
import configparser
import os
from typing import List # Required for type hinting if used

from src.core.storage_interface import StorageInterface
from src.adapters.memory_storage import MemoryStorage
from src.adapters.csv_storage import CsvStorage
from src.adapters.database_storage import DatabaseStorage
from src.adapters.redis_storage import RedisStorage
from src.adapters.mysql_storage import MySQLStorage # Import MySQLStorage

def load_configuration(config_file_path: str = "config/config.ini") -> configparser.ConfigParser:
    """
    Loads configuration settings from the specified INI file.

    Args:
        config_file_path: Path to the configuration file.

    Returns:
        A ConfigParser object populated with settings from the file.

    Raises:
        FileNotFoundError: If the configuration file cannot be found.
    """
    parser = configparser.ConfigParser()
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
    parser.read(config_file_path)
    return parser

def get_storage_adapter(config: configparser.ConfigParser) -> StorageInterface:
    """
    Initializes and returns a storage adapter based on the loaded configuration.

    The type of adapter (e.g., 'memory', 'csv', 'database', 'redis', 'mysql') is read from
    the 'ADAPTER_TYPE' key in the '[DEFAULT]' section of the configuration.
    Specific settings for each adapter type are read from their respective sections
    (e.g., '[csv]', '[database]', '[redis]', '[mysql]').

    Args:
        config: A ConfigParser object containing the application configuration.

    Returns:
        An instance of a class that implements the StorageInterface.

    Raises:
        ValueError: If an unknown ADAPTER_TYPE is specified or required config is missing.
        ConnectionError: If the selected adapter (e.g., Redis, MySQL) fails to connect during initialization.
    """
    adapter_type = config.get('DEFAULT', 'ADAPTER_TYPE', fallback='memory').lower()

    print(f"Selected adapter type from config: {adapter_type}")

    if adapter_type == 'csv':
        filepath = config.get('csv', 'filepath', fallback='data/items.csv')
        fieldnames_str = config.get('csv', 'fieldnames', fallback='id,name,description,data')
        fieldnames_list = [name.strip() for name in fieldnames_str.split(',')]

        csv_dir = os.path.dirname(filepath)
        if csv_dir:
            os.makedirs(csv_dir, exist_ok=True)
        print(f"Initializing CsvStorage with filepath: {filepath}")
        return CsvStorage(filepath=filepath, fieldnames=fieldnames_list)

    elif adapter_type == 'database': # This typically refers to SQLite
        db_url = config.get('database', 'db_url', fallback='sqlite:///./data/items.db')

        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                db_path = db_path[2:]

            db_dir = os.path.dirname(db_path)
            if db_dir:
                 os.makedirs(db_dir, exist_ok=True)
        print(f"Initializing DatabaseStorage (SQLite) with db_url: {db_url}")
        return DatabaseStorage(db_url=db_url)

    elif adapter_type == 'redis':
        redis_url = config.get('redis', 'redis_url', fallback='redis://localhost:6379/0')
        print(f"Initializing RedisStorage with redis_url: {redis_url}")
        try:
            return RedisStorage(redis_url=redis_url) # ConnectionError handled by RedisStorage init
        except ConnectionError as e:
            print(f"Failed to initialize Redis adapter: {e}")
            raise # Re-raise to be caught by main.py

    elif adapter_type == "mysql":
        db_url = config.get("mysql", "db_url", fallback=None)
        if not db_url or 'user:password@host:port/database' in db_url: # Check if it's the placeholder
            raise ValueError("MySQL 'db_url' not configured or is using placeholder values in config/config.ini.")
        print(f"Initializing MySQLStorage with URL: {db_url}")
        try:
            return MySQLStorage(db_url=db_url) # ConnectionError handled by MySQLStorage init
        except ConnectionError as e:
            print(f"Failed to initialize MySQL adapter: {e}")
            raise

    elif adapter_type == 'memory':
        print("Initializing MemoryStorage.")
        return MemoryStorage()

    else:
        raise ValueError(f"Unknown ADAPTER_TYPE: '{adapter_type}'. Supported types are memory, csv, database, redis, mysql.")
