#!/usr/bin/env python3
"""
Script to generate a Fernet encryption key for ENCRYPTION_KEY_FERNET
"""
from cryptography.fernet import Fernet
import base64

if __name__ == "__main__":
    key = Fernet.generate_key()
    key_b64 = base64.b64encode(key).decode()
    
    print("=" * 60)
    print("Generated Fernet Encryption Key")
    print("=" * 60)
    print(f"\nAdd this to your .env file as ENCRYPTION_KEY_FERNET:\n")
    print(key_b64)
    print("\n" + "=" * 60)
