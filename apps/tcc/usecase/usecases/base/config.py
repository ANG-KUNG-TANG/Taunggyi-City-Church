from typing import List

class UseCaseConfiguration:
    def __init__(self):
        self.require_authentication: bool = True
        self.required_roles: List[str] = []
        self.required_permissions: list[str] =[]
        self.transactional: bool=True
        self.validate_input: bool =True
        self.validate_output: bool=True
        self.audit_log:bool =True
        