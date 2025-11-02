from typing import Any, Dict


class ValdationError(Exception):
    
    def __init__(self, message: str, errors: Dict[str, Any]=None):
        self.message = message
        self.errors = errors or {}
        super().__init__(self.message)
        
    def to_dict(self) -> Dict[str, Any]:
        return {"message": self.message, "errors": self.errors}
    
    