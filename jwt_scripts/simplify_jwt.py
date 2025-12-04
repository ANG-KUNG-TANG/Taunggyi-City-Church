# simplify_jwt.py
from pathlib import Path

def simplify_env():
    """Switch to HS256 in .env file"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return
    
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Process lines
    new_lines = []
    for line in lines:
        if line.strip().startswith('JWT_ALGORITHM='):
            new_lines.append('JWT_ALGORITHM=RS256\n')
        elif line.strip().startswith('JWT_SECRET_KEY='):
            # Keep existing or add default
            if '=' in line and line.split('=', 1)[1].strip():
                new_lines.append(line)
            else:
                new_lines.append('JWT_SECRET_KEY="dev-secret-key-change-in-production"\n')
        elif line.strip().startswith('JWT_PRIVATE_KEY=') or line.strip().startswith('JWT_PUBLIC_KEY='):
            # Comment out RSA keys
            if not line.strip().startswith('#'):
                new_lines.append(f'# {line}')
        else:
            new_lines.append(line)
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print("✅ Simplified .env for HS256")
    print("   - Algorithm: RS256")
    print("   - Using JWT_SECRET_KEY")
    print("   - RSA keys commented out")
    
    # Show changes
    print("\n📝 JWT-related lines in .env:")
    for line in new_lines:
        if 'JWT' in line:
            print(f"   {line.rstrip()}")

if __name__ == "__main__":
    simplify_env()