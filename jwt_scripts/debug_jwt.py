# fix_hs256_simple.py
import secrets
import os
from pathlib import Path

print("🔧 Quick Fix for HS256")
print("=" * 50)

# Generate a secure secret key
secret_key = secrets.token_urlsafe(32)
print(f"🔐 Generated secret key: {secret_key}")

# Update .env
env_path = Path(".env")
if env_path.exists():
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('JWT_ALGORITHM='):
            new_lines.append('JWT_ALGORITHM=HS256\n')
        elif stripped.startswith('JWT_SECRET_KEY='):
            new_lines.append(f'JWT_SECRET_KEY="{secret_key}"\n')
        elif stripped.startswith('JWT_PRIVATE_KEY=') or stripped.startswith('JWT_PUBLIC_KEY='):
            # Comment out RSA keys
            if not line.startswith('#'):
                new_lines.append(f'# {line}')
        else:
            new_lines.append(line)
    
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print("✅ Updated .env file")
else:
    print(f"❌ .env not found at {env_path}")
    print(f"\n📝 Create .env with:")
    print(f'JWT_ALGORITHM=HS256')
    print(f'JWT_SECRET_KEY="{secret_key}"')

# Update base.py
base_path = Path("config/settings/base.py")
if base_path.exists():
    with open(base_path, 'r') as f:
        content = f.read()
    
    # 1. Ensure algorithm is HS256
    content = content.replace(
        "'ALGORITHM': env('JWT_ALGORITHM', default='HS256'),",
        "'ALGORITHM': 'HS256',  # Using HS256"
    )
    
    # 2. Ensure JWT_SECRET_KEY is loaded
    if 'JWT_SECRET_KEY = env(' not in content:
        # Find where to insert it (after JWT_CONFIG)
        config_pos = content.find('JWT_CONFIG = {')
        if config_pos != -1:
            # Find end of JWT_CONFIG
            config_end = content.find('\n\n', config_pos)
            if config_end == -1:
                config_end = content.find('\n}', config_pos) + 2
            
            # Insert JWT_SECRET_KEY loading
            content = content[:config_end] + '\nJWT_SECRET_KEY = env("JWT_SECRET_KEY", default="")\n' + content[config_end:]
    
    # 3. Remove or comment RSA key warnings
    warning_text = '''if not JWT_PRIVATE_KEY or not JWT_PUBLIC_KEY:
    print("⚠️  WARNING: JWT keys not loaded properly from .env")'''
    
    if warning_text in content:
        content = content.replace(warning_text, '# RSA key warnings disabled for HS256')
    
    with open(base_path, 'w') as f:
        f.write(content)
    
    print("✅ Updated base.py")
else:
    print(f"❌ base.py not found at {base_path}")

print("\n" + "=" * 50)
print("✅ Fix applied!")
print(f"\n📋 Your new JWT configuration:")
print(f'   Algorithm: HS256')
print(f'   Secret key: {secret_key[:20]}...')
print("\n🚀 Restart Django server with: python manage.py runserver")