#!/usr/bin/env python3
"""
Switch from RS256 to HS256 - FIXED VERSION with encoding handling
"""
import secrets
import re
from pathlib import Path
import base64
import codecs

def generate_secure_secret_key(length=64):
    """Generate a secure random secret key for HS256"""
    return secrets.token_urlsafe(length)

def detect_encoding(file_path):
    """Detect file encoding"""
    encodings = ['utf-8', 'cp1252', 'latin-1', 'iso-8859-1', 'utf-16']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue
    
    # Default to latin-1 (never fails)
    return 'latin-1'

def read_file_safe(file_path):
    """Read a file with proper encoding detection"""
    encoding = detect_encoding(file_path)
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except:
        # Fallback to binary then decode
        with open(file_path, 'rb') as f:
            content = f.read()
            return content.decode('utf-8', errors='replace')

def write_file_safe(file_path, content):
    """Write a file with UTF-8 encoding"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_env_file(secret_key):
    """Update .env file to use HS256 with new secret key"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print(f"❌ .env file not found at: {env_path}")
        return False
    
    print(f"📝 Updating .env file...")
    
    # Read current content safely
    content = read_file_safe(env_path)
    
    # Make changes
    # 1. Change algorithm to HS256
    content = re.sub(
        r'JWT_ALGORITHM\s*=\s*.*',
        f'JWT_ALGORITHM=HS256',
        content
    )
    
    # 2. Add or update JWT_SECRET_KEY
    if 'JWT_SECRET_KEY=' in content:
        content = re.sub(
            r'JWT_SECRET_KEY\s*=\s*"[^"]*"',
            f'JWT_SECRET_KEY="{secret_key}"',
            content
        )
    else:
        # Add after JWT_ALGORITHM
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('JWT_ALGORITHM='):
                lines.insert(i + 1, f'JWT_SECRET_KEY="{secret_key}"')
                break
        content = '\n'.join(lines)
    
    # 3. Comment out RSA keys
    content = re.sub(
        r'^(JWT_PRIVATE_KEY\s*=)',
        r'# \1  # Commented out for HS256',
        content,
        flags=re.MULTILINE
    )
    
    content = re.sub(
        r'^(JWT_PUBLIC_KEY\s*=)',
        r'# \1  # Commented out for HS256',
        content,
        flags=re.MULTILINE
    )
    
    # Backup original
    backup_path = env_path.with_suffix('.env.backup')
    try:
        env_path.rename(backup_path)
        print(f"📦 Backed up original to: {backup_path}")
    except:
        print(f"⚠️  Could not backup, writing directly...")
    
    # Write new content
    write_file_safe(env_path, content)
    
    print(f"✅ Updated .env with HS256 configuration")
    return True

def update_base_py():
    """Update base.py settings for HS256"""
    base_path = Path("config/settings/base.py")
    
    if not base_path.exists():
        print(f"❌ base.py not found at: {base_path}")
        return False
    
    print(f"📝 Updating base.py...")
    
    # Read current content safely
    content = read_file_safe(base_path)
    
    # Create backup
    backup_path = base_path.with_suffix('.py.backup')
    try:
        base_path.rename(backup_path)
        print(f"📦 Backed up original to: {backup_path}")
    except:
        print(f"⚠️  Could not backup, creating new backup file...")
        write_file_safe(backup_path, content)
    
    # 1. Fix algorithm to HS256
    # Try different patterns
    patterns = [
        r"'ALGORITHM'\s*:\s*env\('JWT_ALGORITHM',\s*default=['\"][^'\"]+['\"]\)",
        r'ALGORITHM[\s:]+.*',
    ]
    
    for pattern in patterns:
        if re.search(pattern, content):
            content = re.sub(
                pattern,
                "'ALGORITHM': 'HS256',  # Changed to HS256",
                content
            )
            break
    
    # 2. Add JWT_SECRET_KEY loading if not present
    if 'JWT_SECRET_KEY = env(' not in content:
        # Find a good place to insert (after JWT_CONFIG or before RSA keys)
        insert_point = content.find('JWT_PRIVATE_KEY = env')
        if insert_point == -1:
            insert_point = content.find('JWT_CONFIG = {')
        
        if insert_point != -1:
            # Go back to start of line
            line_start = content.rfind('\n', 0, insert_point) + 1
            indent = content[line_start:insert_point]
            
            # Insert JWT_SECRET_KEY
            new_line = f"{indent}JWT_SECRET_KEY = env('JWT_SECRET_KEY', default='')\n"
            content = content[:insert_point] + new_line + content[insert_point:]
    
    # 3. Remove RSA key warnings
    warning_patterns = [
        r'if not JWT_PRIVATE_KEY or not JWT_PUBLIC_KEY:.*?\n.*?\n.*?\n',
        r'print.*JWT keys not loaded.*',
    ]
    
    for pattern in warning_patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 4. Ensure we're using the right algorithm in REST_FRAMEWORK if present
    if 'SIMPLE_JWT' in content:
        content = re.sub(
            r"'ALGORITHM'\s*:\s*[^,]+",
            "'ALGORITHM': 'HS256'",
            content
        )
    
    # Write updated content
    write_file_safe(base_path, content)
    
    print(f"✅ Updated base.py for HS256")
    return True

def create_simple_update_script():
    """Create a simpler, direct update script"""
    simple_script = '''#!/usr/bin/env python3
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
            new_lines.append('JWT_ALGORITHM=HS256\n')
        elif line.strip().startswith('JWT_SECRET_KEY='):
            new_lines.append(f'JWT_SECRET_KEY="{secret_key}"\n')
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
'''
    
    script_path = Path("simple_switch_hs256.py")
    write_file_safe(script_path, simple_script)
    
    print(f"📄 Created simple switch script: {script_path}")
    return script_path

def verify_changes():
    """Verify the changes were made"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    content = read_file_safe(env_path)
    
    print("\n🔍 Verification:")
    print("-" * 40)
    
    checks = [
        ('JWT_ALGORITHM=HS256' in content, "JWT_ALGORITHM=HS256"),
        ('JWT_SECRET_KEY=' in content, "JWT_SECRET_KEY present"),
        (not any(l.strip().startswith('JWT_PRIVATE_KEY=') and not l.startswith('#') 
                for l in content.split('\n')), "RSA keys commented"),
    ]
    
    all_ok = True
    for check, message in checks:
        if check:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
            all_ok = False
    
    return all_ok

def main():
    print("🔄 Switching from RS256 to HS256 - FIXED VERSION")
    print("=" * 60)
    
    # Generate secret key
    print("\n1️⃣  Generating secure JWT secret key...")
    secret_key = generate_secure_secret_key(32)
    print(f"✅ Generated key: {secret_key[:20]}... ({len(secret_key)} chars)")
    
    # Update .env
    print("\n2️⃣  Updating .env file...")
    if not update_env_file(secret_key):
        print("❌ Failed to update .env")
        return
    
    # Update base.py
    print("\n3️⃣  Updating Django settings...")
    update_base_py()
    
    # Create simple script for future
    print("\n4️⃣  Creating simple update script...")
    create_simple_update_script()
    
    # Verify
    print("\n5️⃣  Verifying changes...")
    verify_changes()
    
    # Final instructions
    print("\n" + "=" * 60)
    print("✅ SWITCH COMPLETE!")
    print(f"\n📋 Your new .env configuration:")
    print(f'   JWT_ALGORITHM=HS256')
    print(f'   JWT_SECRET_KEY="{secret_key}"')
    print("\n🚀 Restart Django with: python manage.py runserver")

if __name__ == "__main__":
    main()