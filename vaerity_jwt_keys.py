# verify_jwt_keys_standalone.py
import os
import sys
import base64
from pathlib import Path

def load_jwt_keys_from_env():
    """Load JWT keys from .env file directly"""
    # Find the project root
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir  # c_backend directory
    env_file = project_root / ".env"
    
    print(f"Looking for .env at: {env_file}")
    
    if not env_file.exists():
        print("❌ .env file not found")
        return None, None
    
    # Read .env file
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove surrounding quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                env_vars[key] = value
    
    # Extract JWT keys
    private_b64 = env_vars.get('JWT_PRIVATE_KEY')
    public_b64 = env_vars.get('JWT_PUBLIC_KEY')
    
    if not private_b64:
        print("❌ JWT_PRIVATE_KEY not found in .env")
    if not public_b64:
        print("❌ JWT_PUBLIC_KEY not found in .env")
    
    return private_b64, public_b64

def decode_key(key_b64, key_name):
    """Decode base64 key and verify format"""
    if not key_b64:
        print(f"❌ {key_name}: Empty")
        return None
    
    print(f"\n🔍 {key_name}:")
    print(f"   Raw length: {len(key_b64)} characters")
    
    try:
        # Decode base64
        decoded = base64.b64decode(key_b64).decode('utf-8')
        print(f"   Decoded length: {len(decoded)} characters")
        
        # Check PEM format
        if decoded.startswith('-----BEGIN') and '-----END' in decoded:
            print(f"   ✅ Valid PEM format")
            
            # Check key type
            if 'PRIVATE KEY' in decoded:
                print(f"   ✅ Contains PRIVATE KEY")
            elif 'PUBLIC KEY' in decoded:
                print(f"   ✅ Contains PUBLIC KEY")
            
            # Check for newlines
            if '\n' in decoded:
                print(f"   ✅ Contains newlines")
            
            return decoded
        else:
            print(f"   ❌ Not in PEM format")
            return decoded
            
    except Exception as e:
        print(f"   ❌ Decoding failed: {e}")
        return None

def main():
    print("🔐 JWT Key Verification (Standalone)")
    print("=" * 60)
    
    # Load keys from .env
    private_b64, public_b64 = load_jwt_keys_from_env()
    
    if not private_b64 or not public_b64:
        print("\n❌ Cannot proceed - keys missing from .env")
        return
    
    # Decode and verify keys
    private_key = decode_key(private_b64, "Private Key (Base64)")
    public_key = decode_key(public_b64, "Public Key (Base64)")
    
    print("\n" + "=" * 60)
    
    if private_key and public_key:
        print("✅ SUCCESS: Keys decoded from .env!")
        
        # Try to load with cryptography (optional)
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            # Test private key
            private_obj = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend()
            )
            print("✅ Private key parsed by cryptography")
            
            # Test public key
            public_obj = serialization.load_pem_public_key(
                public_key.encode(),
                backend=default_backend()
            )
            print("✅ Public key parsed by cryptography")
            
        except ImportError:
            print("⚠️  Cryptography library not available")
        except Exception as e:
            print(f"❌ Cryptography error: {e}")
            
    else:
        print("❌ FAILED: One or both keys are invalid")
        
        # Check if keys might already be in PEM format (not base64)
        print("\n🔍 Checking if keys are already in PEM format...")
        if private_b64.startswith('-----BEGIN'):
            print("⚠️  Private key appears to be in PEM format (not base64)")
            print("   Use the format_keys.py script to convert to base64")
        
        if public_b64.startswith('-----BEGIN'):
            print("⚠️  Public key appears to be in PEM format (not base64)")
            print("   Use the format_keys.py script to convert to base64")

if __name__ == "__main__":
    main()