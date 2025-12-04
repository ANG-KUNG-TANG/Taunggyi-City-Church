# debug_env.py
import re
from pathlib import Path

env_path = Path("c_backend/.env")
print(f"Reading .env from: {env_path}")
print("=" * 60)

with open(env_path, 'r') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
print("\nLooking for problematic lines...")
print("-" * 60)

for i, line in enumerate(lines, 1):
    line = line.rstrip()  # Remove trailing newline
    if not line or line.startswith('#'):
        continue
    
    # Check if line looks like a key=value pair
    if '=' in line:
        key, value = line.split('=', 1)
        key = key.strip()
        
        # Check for JWT keys
        if 'JWT' in key.upper():
            print(f"\nLine {i}: {key}")
            print(f"Value preview: {value[:80]}...")
            
            # Check for common issues
            if '\\n' in value:
                print("  ✓ Contains escaped newlines (\\n)")
            elif '\n' in value:
                print("  ⚠️ Contains actual newlines (problematic!)")
            elif len(value) > 200:
                print(f"  ⚠️ Very long value ({len(value)} chars)")
                
            # Check for BEGIN/END markers
            if '-----BEGIN' in value:
                print("  ✓ Contains PEM markers")
    else:
        # This might be the "invalid line"!
        print(f"\n⚠️ Line {i} (no '=' found, might be invalid):")
        print(f"  {line[:100]}...")