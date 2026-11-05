import re
from typing import Any, Callable, Optional, List, Pattern
from pydantic import field_validator
from datetime import datetime

# Regex patterns
USERNAME_PATTERN: Pattern = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")
EMAIL_PATTERN: Pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_PATTERN: Pattern = re.compile(r"^\+?[\d\s-()]{7,15}$")
PASSWORD_PATTERN: Pattern = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")
BAPTISM_DATE_PATTERN: Pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FAMILY_NAME_PATTERN: Pattern = re.compile(r"^[a-zA-Z\s'-]{2,50}$")

class ValidationRules:
    """Container for all validation rules"""
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> Any:
        """Validate that a required field is not empty"""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{field_name} is required")
        return value
    
    @staticmethod
    def validate_username(value: str) -> str:
        """Validate username format"""
        value = ValidationRules.validate_required(value, "Username")
        value = value.strip()
        
        if not USERNAME_PATTERN.match(value):
            raise ValueError(
                "Username must be 3-30 characters long and contain only letters, numbers, '.', '-', or '_'"
            )
        return value
    
    @staticmethod
    def validate_email(value: str) -> str:
        """Validate email format"""
        value = ValidationRules.validate_required(value, "Email")
        value = value.lower().strip()
        
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Invalid email address format")
        return value
    
    @staticmethod
    def validate_phone(value: Optional[str]) -> Optional[str]:
        """Validate phone number format (optional field)"""
        if not value:
            return None
        
        value = value.strip()
        cleaned_value = re.sub(r'[\s\-()]', '', value)
        
        if not PHONE_PATTERN.match(value):
            raise ValueError("Invalid phone number format")
        return value
    
    @staticmethod
    def validate_password(value: str) -> str:
        """Validate password strength"""
        value = ValidationRules.validate_required(value, "Password")
        
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not PASSWORD_PATTERN.match(value):
            raise ValueError(
                "Password must contain at least one lowercase letter, one uppercase letter, "
                "one digit, and one special character (@$!%*?&)"
            )
        return value
    
    @staticmethod
    def validate_baptism_date(value: Optional[str]) -> Optional[str]:
        """Validate baptism date format"""
        if not value:
            return None
        
        if not BAPTISM_DATE_PATTERN.match(value):
            raise ValueError("Baptism date must be in YYYY-MM-DD format")
        
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid date")
        
        return value
    
    @staticmethod
    def validate_family_name(value: str) -> str:
        """Validate family name for church records"""
        value = ValidationRules.validate_required(value, "Family name")
        value = value.strip()
        
        if not FAMILY_NAME_PATTERN.match(value):
            raise ValueError(
                "Family name must be 2-50 characters long and contain only letters, spaces, hyphens, and apostrophes"
            )
        return value
    
    @staticmethod
    def validate_min_age(age: int, min_age: int = 18) -> int:
        """Validate minimum age requirement"""
        if age < 0:
            raise ValueError("Age cannot be negative")
        
        if age < min_age:
            raise ValueError(f"Must be at least {min_age} years old")
        
        return age

class ValidatorFactory:
    """Factory for creating validators"""
    
    @staticmethod
    def create_length_validator(min_len: int, max_len: int, field_name: str) -> Callable[[str], str]:
        """Create a validator for string length"""
        def validator(value: str) -> str:
            value = ValidationRules.validate_required(value, field_name)
            value = value.strip()
            
            if len(value) < min_len:
                raise ValueError(f"{field_name} must be at least {min_len} characters")
            
            if len(value) > max_len:
                raise ValueError(f"{field_name} cannot exceed {max_len} characters")
            
            return value
        return validator
    
    @staticmethod
    def create_choice_validator(choices: List[Any], field_name: str) -> Callable[[Any], Any]:
        """Create a validator for choice fields"""
        def validator(value: Any) -> Any:
            if value not in choices:
                raise ValueError(
                    f"{field_name} must be one of: {', '.join(map(str, choices))}"
                )
            return value
        return validator

# Common validators as Pydantic field validators
def username_validator(field: str = 'username'):
    """Pydantic validator for username"""
    return field_validator(field)(ValidationRules.validate_username)

def email_validator(field: str = 'email'):
    """Pydantic validator for email"""
    return field_validator(field)(ValidationRules.validate_email)

def phone_validator(field: str = 'phone'):
    """Pydantic validator for phone"""
    return field_validator(field)(ValidationRules.validate_phone)

def password_validator(field: str = 'password'):
    """Pydantic validator for password"""
    return field_validator(field)(ValidationRules.validate_password)

# Pre-defined common validators
validate_full_name = ValidatorFactory.create_length_validator(2, 100, "Full name")
validate_address = ValidatorFactory.create_length_validator(5, 200, "Address")
validate_ministry_name = ValidatorFactory.create_length_validator(3, 50, "Ministry name")