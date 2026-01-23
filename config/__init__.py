"""
SciTeX Web - Configuration Module

This module handles loading, processing, and applying configuration
for the SciTeX Web application.
"""

import os
import json
import logging

# Import Celery app to ensure it's loaded when Django starts
# This allows using @shared_task decorator in apps
from .celery_app import app as celery_app

__all__ = ('celery_app',)

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'server': {
        'port': 3000,
        'host': 'localhost',
        'environment': 'development'
    },
    'api': {
        'baseUrl': '/api',
        'version': 'v1',
        'timeout': 30000
    },
    'auth': {
        'tokenExpiration': 86400,  # 24 hours in seconds
        'refreshTokenExpiration': 604800  # 7 days in seconds
    },
    'features': {
        'enableRealTimeCollaboration': True,
        'enableAI': True,
        'enableVersioning': True
    },
    'storage': {
        'documentPath': './documents',
        'maxUploadSize': 10485760  # 10MB in bytes
    }
}

def loadConfigFiles(config_paths=None):
    """
    Load configuration from JSON files.
    
    Args:
        config_paths (list): List of configuration file paths to load.
            Defaults to ['./config.json', './config.local.json']
            
    Returns:
        dict: Merged configuration from files and defaults
    """
    if config_paths is None:
        config_paths = ['./config.json', './config.local.json']
    
    # Start with default config
    config = DEFAULT_CONFIG.copy()
    
    # Load and merge configuration files
    for path in config_paths:
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    file_config = json.load(f)
                    # Deep merge configurations
                    deep_merge(config, file_config)
                    logger.info(f"Loaded configuration from {path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {path}: {e}")
    
    return config

def deep_merge(target, source):
    """
    Deep merge two dictionaries recursively.
    
    Args:
        target (dict): Target dictionary to merge into
        source (dict): Source dictionary to merge from
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value)
        else:
            target[key] = value

def applyEnvironmentVariables(config):
    """
    Apply environment variables to configuration.
    
    Environment variables override file-based configuration using naming conventions:
    - SERVER_PORT => config.server.port
    - API_BASE_URL => config.api.baseUrl
    
    Args:
        config (dict): Configuration object to apply environment variables to
            
    Returns:
        dict: Configuration with environment variables applied
    """
    # Copy config to avoid modifying original
    config = config.copy()
    
    # Map of environment variables to config paths
    env_map = {
        'PORT': ['server', 'port'],
        'HOST': ['server', 'host'],
        'NODE_ENV': ['server', 'environment'],
        'API_BASE_URL': ['api', 'baseUrl'],
        'API_VERSION': ['api', 'version'],
        'API_TIMEOUT': ['api', 'timeout'],
        'AUTH_TOKEN_EXPIRATION': ['auth', 'tokenExpiration'],
        'AUTH_REFRESH_TOKEN_EXPIRATION': ['auth', 'refreshTokenExpiration'],
        'FEATURE_REALTIME': ['features', 'enableRealTimeCollaboration'],
        'FEATURE_AI': ['features', 'enableAI'],
        'FEATURE_VERSIONING': ['features', 'enableVersioning'],
        'STORAGE_PATH': ['storage', 'documentPath'],
        'STORAGE_MAX_UPLOAD': ['storage', 'maxUploadSize']
    }
    
    # Apply environment variables
    for env_var, path in env_map.items():
        if env_var in os.environ:
            # Navigate to the correct position in the config
            target = config
            for idx, key in enumerate(path):
                if idx == len(path) - 1:
                    # Convert value based on existing type
                    value = os.environ[env_var]
                    existing_type = type(target.get(key, ''))
                    
                    if existing_type == bool:
                        target[key] = value.lower() == 'true'
                    elif existing_type == int:
                        target[key] = int(value)
                    elif existing_type == float:
                        target[key] = float(value)
                    else:
                        target[key] = value
                else:
                    # Ensure path exists
                    if key not in target:
                        target[key] = {}
                    target = target[key]
    
    return config

def setupConfig(config_paths=None):
    """
    Set up the complete application configuration.
    
    This loads configuration from files, applies environment variables,
    and performs any necessary validation or transformation.
    
    Args:
        config_paths (list): List of configuration file paths to load
            
    Returns:
        dict: Complete application configuration
    """
    # Load from files
    config = loadConfigFiles(config_paths)
    
    # Apply environment variables
    config = applyEnvironmentVariables(config)
    
    # Additional setup - validate configuration
    validate_config(config)
    
    return config

def validate_config(config):
    """
    Validate the configuration object.
    
    Args:
        config (dict): Configuration object to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Validate server configuration
    if 'server' not in config:
        raise ValueError("Missing 'server' configuration")
    
    if 'port' not in config['server']:
        raise ValueError("Missing 'server.port' configuration")
    
    # Validate API configuration
    if 'api' not in config:
        raise ValueError("Missing 'api' configuration")
    
    # Validate storage configuration
    if 'storage' in config and 'maxUploadSize' in config['storage']:
        if config['storage']['maxUploadSize'] > 100 * 1024 * 1024:  # 100MB
            logger.warning("maxUploadSize exceeds recommended limit (100MB)")