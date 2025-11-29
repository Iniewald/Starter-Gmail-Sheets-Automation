"""
env_utils.py
------------
Utilities for loading and saving configuration settings using a .env file.

Relies on the `python-dotenv` library for file operations.
"""
import os
from dotenv import load_dotenv, set_key
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load_environment(env_path: str = '.env') -> None:
    """
    Loads environment variables from a .env file into the system environment,
    if the file exists.

    Args:
        env_path: The file path to the .env configuration file. Defaults to ".env".
    """
    if os.path.exists(env_path):
        # The load_dotenv function reads the file and populates os.environ
        load_dotenv(env_path)
        logger.info('Environment variables loaded from %s', env_path)
    else:
        logger.warning("No .env file found at %s. Using system environment variables only.", env_path)


def save_env_setting(key: str, value: str, env_path: str = '.env') -> None:
    """
    Updates or adds a key=value pair in the .env file and sets it in the
    current system environment (os.environ).

    This ensures configuration changes persist across sessions and are immediately
    available in the current runtime.

    Args:
        key: The environment variable name (e.g., 'SPREADSHEET_ID').
        value: The string value to assign to the key.
        env_path: The file path to the .env configuration file. Defaults to ".env".
    """
    # set_key updates the file on disk
    set_key(env_path, key, value)
    # Update the current runtime environment
    os.environ[key] = value
    logger.info("Configuration saved and updated: %s=%s in %s", key, value, env_path)