import re

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w{2,4}$")
PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,}$")

def validate_username(value: str) -> str:
    if not USERNAME_REGEX.match(value):
        raise ValueError("Username must be 3-30 characters long and contain only letters, numbers, '.', '-', or '_'.")
    return value

def validate_email(value: str) -> str:
    if not EMAIL_REGEX.match(value):
        raise ValueError("Invalid email address format.")
    return value.lower()

def validate_phone(value: str) -> str:
    if not PHONE_REGEX.match(value):
        raise ValueError("Invalid phone number format.")
    return value

def validate_password(value: str) -> str:
    if not PASSWORD_REGEX.match(value):
        raise ValueError(
            "Password must be at least 8 characters long, contain one letter, one number, and one special character."
        )
    return value
