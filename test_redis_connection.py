#!/usr/bin/env python3
"""
Test Redis Cloud connection with different SSL configurations
"""

import redis
import ssl

# Your Redis Cloud credentials
REDIS_HOST = "redis-12617.c330.asia-south1-1.gce.redns.redis-cloud.com"
REDIS_PORT = 12617
REDIS_PASSWORD = "BtUjzw407WUWoZueZH5fEb2mdf51oOSC"


def test_redis_connection():
    """Test different Redis connection configurations"""

    print("Testing Redis Cloud connection...")
    print(f"Host: {REDIS_HOST}")
    print(f"Port: {REDIS_PORT}")
    print(f"Password: {'*' * len(REDIS_PASSWORD)}")
    print("-" * 50)

    # Configuration 1: SSL with no certificate verification
    print("1. Testing SSL with no certificate verification...")
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            ssl=True,
            ssl_cert_reqs=ssl.CERT_NONE,
            ssl_check_hostname=False,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        result = client.ping()
        print(f"   ✅ SUCCESS: {result}")
        client.close()
        return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Configuration 2: SSL with default settings
    print("\n2. Testing SSL with default settings...")
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            ssl=True,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        result = client.ping()
        print(f"   ✅ SUCCESS: {result}")
        client.close()
        return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Configuration 3: No SSL (for debugging)
    print("\n3. Testing without SSL...")
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            ssl=False,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        result = client.ping()
        print(f"   ✅ SUCCESS: {result}")
        client.close()
        return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Configuration 4: TLS with specific SSL context
    print("\n4. Testing with custom SSL context...")
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            ssl=True,
            ssl_context=ssl_context,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        result = client.ping()
        print(f"   ✅ SUCCESS: {result}")
        client.close()
        return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    print("\n❌ All connection attempts failed!")
    return False


if __name__ == "__main__":
    success = test_redis_connection()

    if success:
        print("\n🎉 Redis connection working!")
        print("You can now run your main application.")
    else:
        print("\n💥 Redis connection failed!")
        print("Please check your credentials or contact Redis Cloud support.")
