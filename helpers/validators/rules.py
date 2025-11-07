import re
from typing import Any, Callable, Optional
from exceptions import RuleValidationError

# Regex patterns
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile(r"^\+?[\d\s-()]{7,15}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")

# Church-specific validation rules
BAPTISM_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FAMILY_NAME_REGEX = re.compile(r"^[a-zA-Z\s'-]{2,50}$")


def validate_username(value: str) -> str:
    """Validate username format"""
    if not value:
        raise RuleValidationError("username", "Username is required")
    
    if not USERNAME_REGEX.match(value):
        raise RuleValidationError(
            "username", 
            "Username must be 3-30 characters long and contain only letters, numbers, '.', '-', or '_'"
        )
    return value.strip()


def validate_email(value: str) -> str:
    """Validate email format"""
    if not value:
        raise RuleValidationError("email", "Email is required")
    
    if not EMAIL_REGEX.match(value):
        raise RuleValidationError("email", "Invalid email address format")
    return value.lower().strip()


def validate_phone(value: Optional[str]) -> Optional[str]:
    """Validate phone number format (optional field)"""
    if not value:  # Phone is optional, so empty is OK
        return None
    
    cleaned_value = re.sub(r'[\s\-()]', '', value)  # Remove common separators
    
    if not PHONE_REGEX.match(cleaned_value):
        raise RuleValidationError("phone", "Invalid phone number format")
    return value.strip()


def validate_password(value: str) -> str:
    """Validate password strength"""
    if not value:
        raise RuleValidationError("password", "Password is required")
    
    if len(value) < 8:
        raise RuleValidationError("password", "Password must be at least 8 characters long")
    
    if not any(c.islower() for c in value):
        raise RuleValidationError("password", "Password must contain at least one lowercase letter")
    
    if not any(c.isupper() for c in value):
        raise RuleValidationError("password", "Password must contain at least one uppercase letter")
    
    if not any(c.isdigit() for c in value):
        raise RuleValidationError("password", "Password must contain at least one digit")
    
    if not any(c in '@$!%*?&' for c in value):
        raise RuleValidationError("password", "Password must contain at least one special character (@$!%*?&)")
    
    return value


def validate_baptism_date(value: Optional[str]) -> Optional[str]:
    """Validate baptism date format"""
    if not value:
        return None
    
    if not BAPTISM_DATE_REGEX.match(value):
        raise RuleValidationError("baptism_date", "Baptism date must be in YYYY-MM-DD format")
    
    # Additional date validation could be added here
    try:
        from datetime import datetime
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        raise RuleValidationError("baptism_date", "Invalid date")
    
    return value


def validate_family_name(value: str) -> str:
    """Validate family name for church records"""
    if not value:
        raise RuleValidationError("family_name", "Family name is required")
    
    if not FAMILY_NAME_REGEX.match(value):
        raise RuleValidationError(
            "family_name",
            "Family name must be 2-50 characters long and contain only letters, spaces, hyphens, and apostrophes"
        )
    return value.strip()


def validate_min_age(age: int, field_name: str = "age") -> int:
    """Validate minimum age requirement"""
    if age < 0:
        raise RuleValidationError(field_name, "Age cannot be negative")
    
    if age < 18:
        raise RuleValidationError(field_name, "Must be at least 18 years old")
    
    return age


# Validator factory functions
def create_length_validator(min_len: int, max_len: int, field_name: str) -> Callable[[str], str]:
    """Create a validator for string length"""
    def validator(value: str) -> str:
        if not value:
            raise RuleValidationError(field_name, f"{field_name} is required")
        
        if len(value) < min_len:
            raise RuleValidationError(field_name, f"{field_name} must be at least {min_len} characters")
        
        if len(value) > max_len:
            raise RuleValidationError(field_name, f"{field_name} cannot exceed {max_len} characters")
        
        return value.strip()
    return validator


def create_choice_validator(choices: list, field_name: str) -> Callable[[Any], Any]:
    """Create a validator for choice fields"""
    def validator(value: Any) -> Any:
        if value not in choices:
            raise RuleValidationError(
                field_name, 
                f"{field_name} must be one of: {', '.join(map(str, choices))}"
            )
        return value
    return validator


# Common validators
validate_full_name = create_length_validator(2, 100, "full_name")
validate_address = create_length_validator(5, 200, "address")
validate_ministry_name = create_length_validator(3, 50, "ministry_name")