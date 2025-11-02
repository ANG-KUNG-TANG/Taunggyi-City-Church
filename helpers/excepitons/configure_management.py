from pydantic import BaseSettings
from typing import Dict, Any, List, Optional

class ErrorHandlingConfig(BaseSettings):
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "app.log"
    error_log_file: str = "errors.log"
    enable_structured_logging: bool = True
    
    # Error Handling
    show_detailed_errors: bool = False  # Set to False in production
    enable_error_monitoring: bool = True
    error_buffer_size: int = 1000
    
    # Alerting
    enable_alerting: bool = False
    alert_rules: List[Dict[str, Any]] = []
    
    # External Services
    sentry_dsn: Optional[str] = None
    datadog_api_key: Optional[str] = None
    
    class Config:
        env_prefix = "ERROR_HANDLING_"