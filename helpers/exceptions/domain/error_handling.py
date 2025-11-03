from pydantic import BaseSettings
from typing import Dict, Any, List, Optional


class ErrorHandlingConfig(BaseSettings):
    """
    Configuration for error handling system
    """
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    error_log_file: str = "logs/errors.log"
    enable_structured_logging: bool = True
    
    # Error Handling
    show_detailed_errors: bool = False  # Set to False in production
    enable_error_monitoring: bool = True
    error_buffer_size: int = 1000
    
    # Alerting
    enable_alerting: bool = False
    alert_rules: List[Dict[str, Any]] = []
    
    # External Services Monitoring
    sentry_dsn: Optional[str] = None
    datadog_api_key: Optional[str] = None
    
    # Church-specific settings
    enable_church_domain_errors: bool = True
    max_bulk_operation_size: int = 1000
    
    class Config:
        env_prefix = "ERROR_HANDLING_"
        case_sensitive = False


# Default configuration instance
default_config = ErrorHandlingConfig()