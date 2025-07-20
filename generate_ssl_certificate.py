#!/usr/bin/env python3
"""
Generate SSL certificate for local HTTPS development
"""

import subprocess
import sys
import os
from pathlib import Path


def generate_ssl_certificate():
    """Generate self-signed SSL certificate for localhost"""

    print("Generating SSL certificate for localhost...")

    # Create ssl directory
    ssl_dir = Path("ssl")
    ssl_dir.mkdir(exist_ok=True)

    cert_file = ssl_dir / "cert.pem"
    key_file = ssl_dir / "key.pem"

    try:
        # Generate private key and certificate
        cmd = [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:4096",
            "-keyout",
            str(key_file),
            "-out",
            str(cert_file),
            "-days",
            "365",
            "-nodes",
            "-subj",
            "/C=US/ST=Dev/L=LocalHost/O=MaiChart/CN=localhost",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ SSL certificate generated successfully!")
            print(f"Certificate: {cert_file}")
            print(f"Private Key: {key_file}")
            return str(cert_file), str(key_file)
        else:
            print("❌ Failed to generate certificate using OpenSSL")
            print("Trying alternative method...")
            return generate_python_ssl()

    except FileNotFoundError:
        print("❌ OpenSSL not found. Using Python alternative...")
        return generate_python_ssl()


def generate_python_ssl():
    """Generate SSL certificate using Python cryptography library"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime

        print("Generating certificate using Python cryptography...")

        # Create ssl directory
        ssl_dir = Path("ssl")
        ssl_dir.mkdir(exist_ok=True)

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Dev"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "LocalHost"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MaiChart"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.IPAddress("127.0.0.1"),
                    ]
                ),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        # Write certificate and key files
        cert_file = ssl_dir / "cert.pem"
        key_file = ssl_dir / "key.pem"

        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        with open(key_file, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        print("✅ SSL certificate generated successfully!")
        print(f"Certificate: {cert_file}")
        print(f"Private Key: {key_file}")
        return str(cert_file), str(key_file)

    except ImportError:
        print("❌ cryptography library not installed")
        print("Please install it: pip install cryptography")
        return None, None


def main():
    cert_file, key_file = generate_ssl_certificate()

    if cert_file and key_file:
        print("\n🎉 SSL certificate ready!")
        print("\nTo run your app with HTTPS:")
        print("python app.py")
        print("\nThen open: https://localhost:5001")
        print("\n⚠️  Your browser will show a security warning.")
        print("Click 'Advanced' → 'Proceed to localhost (unsafe)'")
        print("This is normal for self-signed certificates.")
    else:
        print("\n❌ Failed to generate SSL certificate")
        print("You can still test file upload, but not microphone recording")


if __name__ == "__main__":
    main()