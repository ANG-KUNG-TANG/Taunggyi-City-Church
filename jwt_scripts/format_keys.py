# format_keys.py
import base64
from pathlib import Path

def encode_key_for_env(key_text):
    """Convert PEM key to base64 for .env storage"""
    # Remove any existing whitespace issues
    key_text = key_text.strip()
    
    # Encode to base64 (single line)
    key_b64 = base64.b64encode(key_text.encode()).decode('utf-8')
    
    # Also create escaped version as fallback
    key_escaped = key_text.replace('\n', '\\n').replace('"', '\\"')
    
    return key_b64, key_escaped, key_text

def main():
    """Format JWT keys for .env file"""
    keys_dir = Path("jwt_keys")
    
    # Read keys
    private_key = (keys_dir / "private.pem").read_text()
    public_key = (keys_dir / "public.pem").read_text()
    
    # Encode keys
    private_b64, private_escaped, private_original = encode_key_for_env(private_key)
    public_b64, public_escaped, public_original = encode_key_for_env(public_key)
    
    print("\n" + "="*60)
    print("=== FOR .env FILE (Base64 Encoded - RECOMMENDED) ===")
    print("="*60)
    print(f'JWT_PRIVATE_KEY="{private_b64}"')
    print(f'\nJWT_PUBLIC_KEY="{public_b64}"')
    
    print("\n" + "="*60)
    print("=== FOR .env FILE (Escaped Newlines - Alternative) ===")
    print("="*60)
    print(f'JWT_PRIVATE_KEY="{private_escaped}"')
    print(f'\nJWT_PUBLIC_KEY="{public_escaped}"')
    
    print("\n" + "="*60)
    print("=== VERIFICATION ===")
    print("="*60)
    # Verify encoding works
    try:
        decoded_private = base64.b64decode(private_b64).decode('utf-8')
        decoded_public = base64.b64decode(public_b64).decode('utf-8')
        if decoded_private == private_original and decoded_public == public_original:
            print("✅ Base64 encoding verified successfully")
        else:
            print("❌ Base64 encoding verification failed")
    except Exception as e:
        print(f"❌ Error during verification: {e}")

if __name__ == "__main__":
    main()