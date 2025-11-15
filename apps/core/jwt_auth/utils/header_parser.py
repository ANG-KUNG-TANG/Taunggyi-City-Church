def extract_bearer_token(auth_header: str) -> str:
    """
    Extract token from Authorization header
    Returns None if header is invalid
    """
    if not auth_header:
        return None
    
    parts = auth_header.split()
    
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]