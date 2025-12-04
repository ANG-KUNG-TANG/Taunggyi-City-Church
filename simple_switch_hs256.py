#!/usr/bin/env python3
"""
Simple script to switch to HS256
"""
import secrets
import os

# Generate a secret key
secret_key = secrets.token_urlsafe(32)

print("🔐 Switching to HS256")
print("=" * 50)
print(f"Generated secret key: {secret_key[:20]}...")
print()

# Update .env file
env_path = ".env"
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.strip().startswith('JWT_ALGORITHM='):
            new_lines.append('JWT_ALGORITHM=HS256
')
        elif line.strip().startswith('JWT_SECRET_KEY='):
            new_lines.append(f'JWT_SECRET_KEY="{secret_key}"
')
        elif line.strip().startswith('JWT_PRIVATE_KEY=') or line.strip().startswith('JWT_PUBLIC_KEY='):
            if not line.startswith('#'):
                new_lines.append(f'# {line}')
        else:
            new_lines.append(line)
    
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print("✅ Updated .env file")
    print(f"   - Algorithm: HS256")
    print(f"   - Secret key set")
    print(f"   - RSA keys commented out")
else:
    print("❌ .env file not found!")
    print(f"Create .env with:")
    print(f'JWT_ALGORITHM=HS256')
    print(f'JWT_SECRET_KEY="{secret_key}"')

print()
print("🔧 Manual steps for base.py:")
print("   1. Change JWT_ALGORITHM to 'HS256'")
print("   2. Add: JWT_SECRET_KEY = env('JWT_SECRET_KEY', default='')")
print("   3. Comment out JWT_PRIVATE_KEY and JWT_PUBLIC_KEY if needed")
print()
print("🚀 Restart Django server to apply changes!")
