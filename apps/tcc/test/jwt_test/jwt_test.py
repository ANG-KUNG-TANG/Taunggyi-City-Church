# test_django_jwt.py
import os
import django
import sys

# Set up Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

try:
    django.setup()
    
    # Now import your settings
    from django.conf import settings
    
    print("🔐 Testing JWT Keys in Django Settings")
    print("=" * 60)
    
    # Check if keys exist
    has_private = hasattr(settings, 'JWT_PRIVATE_KEY') and settings.JWT_PRIVATE_KEY
    has_public = hasattr(settings, 'JWT_PUBLIC_KEY') and settings.JWT_PUBLIC_KEY
    
    print(f"JWT_PRIVATE_KEY loaded: {'✅' if has_private else '❌'}")
    print(f"JWT_PUBLIC_KEY loaded: {'✅' if has_public else '❌'}")
    
    if has_private:
        key = settings.JWT_PRIVATE_KEY
        print(f"\n🔍 JWT_PRIVATE_KEY:")
        print(f"   Type: {type(key)}")
        print(f"   Length: {len(key) if key else 0}")
        print(f"   First 30 chars: {key[:30] if key else 'N/A'}")
        
        if key and key.startswith('-----BEGIN'):
            print("   ✅ Appears to be valid PEM")
        else:
            print("   ❌ Does not appear to be PEM format")
    
    if has_public:
        key = settings.JWT_PUBLIC_KEY
        print(f"\n🔍 JWT_PUBLIC_KEY:")
        print(f"   Type: {type(key)}")
        print(f"   Length: {len(key) if key else 0}")
        print(f"   First 30 chars: {key[:30] if key else 'N/A'}")
        
        if key and key.startswith('-----BEGIN'):
            print("   ✅ Appears to be valid PEM")
        else:
            print("   ❌ Does not appear to be PEM format")
    
    print("\n" + "=" * 60)
    
    # Try to use the keys
    try:
        import jwt
        from datetime import datetime, timedelta
        
        payload = {
            'test': 'data',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow(),
        }
        
        # Try to generate a token
        token = jwt.encode(
            payload,
            settings.JWT_PRIVATE_KEY,
            algorithm='RS256'
        )
        print(f"✅ Token generated: {token[:50]}...")
        
        # Try to decode it
        decoded = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=['RS256']
        )
        print(f"✅ Token verified")
        
    except Exception as e:
        print(f"❌ JWT test failed: {e}")
        
except Exception as e:
    print(f"❌ Django setup failed: {e}")