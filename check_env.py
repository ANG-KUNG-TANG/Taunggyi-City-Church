# check_env.py
from pathlib import Path

# Check .env file
env_path = Path(__file__).parent / ".env"
print(f"📁 .env path: {env_path}")
print(f"   Exists: {env_path.exists()}")

if env_path.exists():
    with open(env_path, 'r') as f:
        lines = f.readlines()
        jwt_lines = [l for l in lines if 'JWT_' in l]
        print(f"\n🔍 Found {len(jwt_lines)} JWT lines:")
        for line in jwt_lines[:3]:  # Show first 3
            print(f"   {line.strip()[:80]}...")
        
        if len(jwt_lines) > 3:
            print(f"   ... and {len(jwt_lines) - 3} more")

# Check jwt_keys directory
keys_dir = Path(__file__).parent / "jwt_keys"
print(f"\n📁 jwt_keys path: {keys_dir}")
print(f"   Exists: {keys_dir.exists()}")

if keys_dir.exists():
    pem_files = list(keys_dir.glob("*.pem"))
    print(f"   Found {len(pem_files)} .pem files:")
    for f in pem_files:
        print(f"   - {f.name} ({f.stat().st_size} bytes)")