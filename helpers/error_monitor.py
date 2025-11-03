from dataclasses import dataclass, asdict
import datetime
import logging
from typing import Any, Dict, List, Callable, Optional

@dataclass
class ErrorEvent:
    exception: Exception
    context: Dict[str, Any]
    timestamp: datetime.datetime
    severity: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['exception_type'] = type(self.exception).__name__
        data['exception_message'] = str(self.exception)
        data['timestamp'] = self.timestamp.isoformat()
        data.pop('exception')
        return data

class ErrorMonitor:
    def __init__(self, max_buffer_size: int = 1000):
        self._subscribers: List[Callable[[ErrorEvent], None]] = []
        self._error_buffer: List[ErrorEvent] = []
        self._max_buffer_size = max_buffer_size
        self._logger = logging.getLogger(__name__)

    def subscribe(self, callback: Callable[[ErrorEvent], None]) -> None:
        self._subscribers.append(callback)

    def notify(self, error_event: ErrorEvent) -> None:
        self._buffer_error(error_event)
        for subscriber in self._subscribers:
            try:
                subscriber(error_event)
            except Exception as e:
                self._logger.error(f"Error in subscriber: {e}")

    def _buffer_error(self, error_event: ErrorEvent) -> None:
        self._error_buffer.append(error_event)
        if len(self._error_buffer) > self._max_buffer_size:
            self._error_buffer.pop(0)

    def get_recent_errors(self, count: int = 100) -> List[ErrorEvent]:
        return self._error_buffer[-count:] if self._error_buffer else []

class AlertManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._alert_rules = self._load_alert_rules()
        self._logger = logging.getLogger(__name__)

    def evaluate_alert(self, error_event: ErrorEvent) -> bool:
        for rule in self._alert_rules:
            if self._matches_rule(error_event, rule):
                self._trigger_alert(error_event, rule)
                return True
        return False

    def _matches_rule(self, error_event: ErrorEvent, rule: Dict) -> bool:
        severity_levels = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}
        if 'min_severity' in rule:
            event_severity = severity_levels.get(error_event.severity, 0)
            min_severity = severity_levels.get(rule['min_severity'], 0)
            if event_severity < min_severity:
                return False
        if 'error_types' in rule:
            error_type = type(error_event.exception).__name__
            if error_type not in rule['error_types']:
                return False
        return True

    def _trigger_alert(self, error_event: ErrorEvent, rule: Dict) -> None:
        alert_message = f"ALERT: {error_event.severity} - {type(error_event.exception).__name__}: {error_event.exception}"
        self._logger.error(alert_message)
        # Add Slack/Email integration here if needed

    def _load_alert_rules(self) -> List[Dict]:
        return [
            {'name': 'critical_errors', 'min_severity': 'CRITICAL'},
            {'name': 'auth_errors', 'error_types': ['AuthenticationException', 'PermissionException']},
        ]