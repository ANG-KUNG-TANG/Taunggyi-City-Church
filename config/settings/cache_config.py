"""
Cache Configuration for Custom Cache Operations
"""
import os
from typing import Dict, Any

# Cache TTL Configuration
CACHE_DEFAULT_TTL = int(os.getenv('CACHE_DEFAULT_TTL', 300))
CACHE_USER_TTL = int(os.getenv('CACHE_USER_TTL', 1800))
CACHE_SESSION_TTL = int(os.getenv('CACHE_SESSION_TTL', 3600))
CACHE_BLACKLIST_TTL = int(os.getenv('CACHE_BLACKLIST_TTL', 86400))

# Redis Configuration for custom cache operations
REDIS_CONFIG = {
    'KEY_PREFIX': 'snowflake',
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASSWORD'),
    'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', 20)),
    'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', 5)),
    'socket_connect_timeout': int(os.getenv('REDIS_CONNECT_TIMEOUT', 5)),
    'retry_on_timeout': True,
    'health_check_interval': int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', 30))
}

# Cache Namespace Configuration
CACHE_NAMESPACES = {
    'user': 'user',
    'session': 'session',
    'rate_limit': 'rate_limit',
    'blacklist': 'blacklist',
    'config': 'config'
}

# Circuit Breaker Configuration
CIRCUIT_BREAKER_CONFIG = {
    'failure_threshold': int(os.getenv('CIRCUIT_BREAKER_FAILURE_THRESHOLD', 5)),
    'recovery_timeout': int(os.getenv('CIRCUIT_BREAKER_RECOVERY_TIMEOUT', 60)),
    'expected_exceptions': (Exception,)
}

# Retry Configuration
RETRY_CONFIG = {
    'max_attempts': int(os.getenv('CACHE_RETRY_ATTEMPTS', 3)),
    'delay': float(os.getenv('CACHE_RETRY_DELAY', 1.0)),
    'backoff': float(os.getenv('CACHE_RETRY_BACKOFF', 2.0)),
    'max_delay': float(os.getenv('CACHE_RETRY_MAX_DELAY', 30.0))
}

# Monitoring Configuration
CACHE_METRICS_ENABLED = os.getenv('CACHE_METRICS_ENABLED', 'True').lower() == 'true'
CACHE_HEALTH_CHECK_INTERVAL = int(os.getenv('CACHE_HEALTH_CHECK_INTERVAL', 30))