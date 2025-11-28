from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Dict


@dataclass
class OperationContext:
    operation_id:str
    user: Optional[Any]
    input_data: Any
    output_data: Any = None
    error: Optional[Exception] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    