"""
Token Extraction Debugger
Add this middleware temporarily to debug what's being sent

Add to settings.py MIDDLEWARE:
    'apps.core.jwt.token_debugger.TokenDebugMiddleware',
"""

import logging
import json

logger = logging.getLogger(__name__)


class TokenDebugMiddleware:
    """
    Middleware to debug JWT token extraction issues
    REMOVE THIS IN PRODUCTION - FOR DEBUGGING ONLY
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only debug for protected endpoints
        if request.path.startswith('/tcc/users/'):
            self.debug_request(request)
        
        response = self.get_response(request)
        return response
    
    def debug_request(self, request):
        """Debug the incoming request"""
        print("\n" + "="*80)
        print("TOKEN EXTRACTION DEBUG")
        print("="*80)
        
        print(f"\nPath: {request.path}")
        print(f"Method: {request.method}")
        
        # Check Authorization header
        print("\n--- Authorization Header ---")
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header:
            print(f"Raw value: '{auth_header}'")
            print(f"Length: {len(auth_header)}")
            print(f"Type: {type(auth_header)}")
            print(f"Repr: {repr(auth_header)}")
            
            # Character analysis
            if len(auth_header) < 200:
                print(f"Characters: {[c for c in auth_header[:100]]}")
            
            # Check for common issues
            if auth_header.startswith('"') or auth_header.startswith("'"):
                print("⚠️  WARNING: Header starts with quote!")
            if ' Bearer' in auth_header or 'Bearer ' not in auth_header[:10]:
                print("⚠️  WARNING: 'Bearer' keyword issue!")
            if '\n' in auth_header or '\r' in auth_header:
                print("⚠️  WARNING: Newline characters found!")
            
            # Try to extract token
            parts = auth_header.split()
            print(f"\nSplit by space: {len(parts)} parts")
            for i, part in enumerate(parts[:3]):  # Show first 3 parts
                print(f"  Part {i}: '{part[:50]}...' (length: {len(part)})")
            
            # Check if it looks like a valid JWT
            if len(parts) >= 2:
                potential_token = parts[1]
                jwt_parts = potential_token.split('.')
                print(f"\nPotential token has {len(jwt_parts)} parts (should be 3)")
                if len(jwt_parts) == 3:
                    print("✓ Token format looks correct")
                else:
                    print("✗ Token format is WRONG!")
        else:
            print("❌ No Authorization header found!")
        
        # Check cookies
        print("\n--- Cookies ---")
        if request.COOKIES:
            for key, value in request.COOKIES.items():
                if 'token' in key.lower():
                    print(f"{key}: '{value[:50]}...' (length: {len(value)})")
        else:
            print("No cookies found")
        
        # Check all headers
        print("\n--- All Request Headers ---")
        for key, value in request.META.items():
            if key.startswith('HTTP_') or key in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
                safe_value = value[:100] if len(value) > 100 else value
                print(f"{key}: {safe_value}")
        
        print("\n" + "="*80 + "\n")


def test_token_string(token_string: str):
    """
    Test if a token string is valid
    
    Usage:
        from apps.core.jwt.token_debugger import test_token_string
        test_token_string("Bearer eyJ0eXAi...")
    """
    print("\n" + "="*80)
    print("TOKEN STRING TEST")
    print("="*80)
    
    print(f"\nInput: '{token_string}'")
    print(f"Length: {len(token_string)}")
    print(f"Type: {type(token_string)}")
    print(f"Repr: {repr(token_string)}")
    
    # Step 1: Strip whitespace
    cleaned = token_string.strip()
    print(f"\n1. After strip(): '{cleaned[:50]}...'")
    print(f"   Length: {len(cleaned)}")
    
    # Step 2: Remove quotes
    if (cleaned.startswith('"') and cleaned.endswith('"')) or \
       (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1]
        print(f"2. After removing quotes: '{cleaned[:50]}...'")
    
    # Step 3: Check for Bearer prefix
    if cleaned.lower().startswith('bearer '):
        token = cleaned[7:].strip()
        print(f"3. After removing 'Bearer ': '{token[:50]}...'")
    else:
        token = cleaned
        print(f"3. No 'Bearer' prefix found")
    
    # Step 4: Check JWT format
    parts = token.split('.')
    print(f"\n4. JWT parts: {len(parts)}")
    
    if len(parts) == 3:
        print("   ✓ Correct number of parts")
        print(f"   Header length: {len(parts[0])}")
        print(f"   Payload length: {len(parts[1])}")
        print(f"   Signature length: {len(parts[2])}")
        
        # Try to decode
        import jwt
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            print("\n✓ Token successfully decoded (no verification)")
            print(f"   Payload: {json.dumps(decoded, indent=2)}")
        except Exception as e:
            print(f"\n✗ Failed to decode: {e}")
    else:
        print(f"   ✗ WRONG number of parts! Expected 3, got {len(parts)}")
        if len(parts) > 0:
            for i, part in enumerate(parts):
                print(f"   Part {i}: '{part[:30]}...' (length: {len(part)})")
    
    print("\n" + "="*80 + "\n")


def simulate_request_with_token(token: str, use_bearer: bool = True):
    """
    Simulate how Django would receive the token
    
    Usage:
        from apps.core.jwt.token_debugger import simulate_request_with_token
        simulate_request_with_token("eyJ0eXAi...")
    """
    print("\n" + "="*80)
    print("REQUEST SIMULATION")
    print("="*80)
    
    # Simulate different ways the token might be sent
    scenarios = []
    
    if use_bearer:
        scenarios = [
            ("Correct: 'Bearer <token>'", f"Bearer {token}"),
            ("Extra spaces: 'Bearer  <token>'", f"Bearer  {token}"),
            ("Quoted: '\"Bearer <token>\"'", f'"Bearer {token}"'),
            ("Single quoted: \"'Bearer <token>'\"", f"'Bearer {token}'"),
            ("Lowercase: 'bearer <token>'", f"bearer {token}"),
            ("No space: 'Bearer<token>'", f"Bearer{token}"),
        ]
    else:
        scenarios = [
            ("Just token", token),
            ("Quoted token", f'"{token}"'),
            ("Single quoted token", f"'{token}'"),
        ]
    
    for name, auth_header in scenarios:
        print(f"\n--- Scenario: {name} ---")
        print(f"Header value: '{auth_header[:80]}...'")
        
        # Simulate extraction
        try:
            # Method 1: Split
            parts = auth_header.strip().split(None, 1)
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                extracted = parts[1]
                print(f"✓ Extracted via split: '{extracted[:50]}...'")
            elif len(parts) == 1:
                extracted = parts[0]
                print(f"⚠️  No Bearer prefix, using whole string: '{extracted[:50]}...'")
            
            # Check JWT format
            jwt_parts = extracted.strip().strip('"\'').split('.')
            if len(jwt_parts) == 3:
                print(f"✓ Valid JWT format ({len(jwt_parts)} parts)")
            else:
                print(f"✗ Invalid JWT format ({len(jwt_parts)} parts)")
                
        except Exception as e:
            print(f"✗ Extraction failed: {e}")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    # Example usage
    print("Token Debugger loaded. Use these functions:")
    print("  - test_token_string('Bearer eyJ...')")
    print("  - simulate_request_with_token('eyJ...')")
    print("  - Add TokenDebugMiddleware to settings.MIDDLEWARE")