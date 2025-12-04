#!/usr/bin/env python3
"""
Generate RSA keys for JWT without OpenSSL
"""
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def generate_rsa_keys(key_size=4096):
    """Generate RSA key pair"""
    print(f"🔐 Generating {key_size}-bit RSA keys...")
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    # Private key in PKCS8 format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Public key
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem

def main():
    # Create directory
    keys_dir = Path("jwt_keys")
    keys_dir.mkdir(exist_ok=True)
    
    # Generate keys
    private_key, public_key = generate_rsa_keys(4096)
    
    # Save files
    with open(keys_dir / "private.pem", "w") as f:
        f.write(private_key)
    
    with open(keys_dir / "public.pem", "w") as f:
        f.write(public_key)
    
    print("✅ Keys generated successfully!")
    print(f"📁 Private key: {keys_dir}/private.pem")
    print(f"📁 Public key: {keys_dir}/public.pem")
    
    # Show for .env file
    print("\n" + "="*50)
    print("For your .env file:")
    print("="*50)
    print(f'\nJWT_PRIVATE_KEY="""{private_key}"""')
    print(f'\nJWT_PUBLIC_KEY="""{public_key}"""')
    
    # Generate development keys too (2048-bit)
    print("\n" + "="*50)
    print("Generating development keys (2048-bit)...")
    dev_private, dev_public = generate_rsa_keys(2048)
    
    with open(keys_dir / "private_dev.pem", "w") as f:
        f.write(dev_private)
    
    with open(keys_dir / "public_dev.pem", "w") as f:
        f.write(dev_public)
    
    print(f"📁 Dev private key: {keys_dir}/private_dev.pem")
    print(f"📁 Dev public key: {keys_dir}/public_dev.pem")

if __name__ == "__main__":
    main()