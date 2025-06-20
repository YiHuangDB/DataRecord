import uvicorn
import os
import configparser # For catching configparser.Error

from src.api import routes
from src.core.config import load_configuration, get_storage_adapter

# General data directory, can be used by multiple adapters if needed.
# Individual adapters also handle their specific path creations.
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_FILE = "config/config.ini"

if __name__ == "__main__":
    try:
        print(f"Loading configuration from: {CONFIG_FILE}")
        config = load_configuration(config_file_path=CONFIG_FILE)

        adapter_type = config.get('DEFAULT', 'ADAPTER_TYPE', fallback='memory').lower()
        print(f"Attempting to initialize '{adapter_type}' storage adapter...")

        routes.storage_adapter = get_storage_adapter(config)

        print(f"Successfully initialized '{adapter_type}' storage adapter.")

        # Specific check for Redis to provide immediate feedback during startup
        if adapter_type == 'redis':
            try:
                # routes.storage_adapter is RedisStorage, redis_client is an attribute
                if hasattr(routes.storage_adapter, 'redis_client'):
                    routes.storage_adapter.redis_client.ping() # type: ignore
                    print("Successfully connected to Redis server.")
            except Exception as e: # Catching redis.exceptions.ConnectionError or broader
                print(f"Failed to connect to Redis server specified in config: {e}")
                print("Please ensure Redis server is running and configuration is correct.")
                # Depending on policy, you might want to exit if critical storage is unavailable
                # exit(1)

    except FileNotFoundError as e:
        print(f"Configuration Error: {e}. Please ensure '{CONFIG_FILE}' exists.")
        print("Falling back to default MemoryStorage.")
        routes.storage_adapter = get_storage_adapter(configparser.ConfigParser()) # Get default memory adapter
    except (ValueError, configparser.Error, ConnectionError) as e: # Catch specific errors from config/adapter loading
        print(f"Error initializing storage adapter: {e}")
        print("Falling back to default MemoryStorage.")
        # Create a default config parser if loading failed, to get MemoryStorage
        default_config = configparser.ConfigParser()
        default_config['DEFAULT'] = {'ADAPTER_TYPE': 'memory'}
        routes.storage_adapter = get_storage_adapter(default_config)
    except Exception as e: # Catch-all for any other unexpected errors
        print(f"An unexpected error occurred during initialization: {e}")
        print("Falling back to default MemoryStorage.")
        default_config = configparser.ConfigParser()
        default_config['DEFAULT'] = {'ADAPTER_TYPE': 'memory'}
        routes.storage_adapter = get_storage_adapter(default_config)


    uvicorn.run(routes.app, host="0.0.0.0", port=8000)
