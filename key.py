#!/usr/bin/env python3
"""
Generate a secure secret key for Flask
"""

import secrets
import string


def generate_secret_key(length=50):
    """Generate a secure random secret key"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    secret_key = "".join(secrets.choice(alphabet) for _ in range(length))
    return secret_key


if __name__ == "__main__":
    secret = generate_secret_key()
    print("Generated secure secret key:")
    print(f"SECRET_KEY={secret}")
    print("\nTo use this, run:")
    print(f"set SECRET_KEY={secret}")
    print("python app.py")
