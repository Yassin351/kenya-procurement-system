import os
import sys

filepath = 'tests/conftest.py'

# Force delete if exists
if os.path.exists(filepath):
    try:
        os.remove(filepath)
        print(f"Deleted: {filepath}")
    except Exception as e:
        print(f"Error deleting: {e}")
        sys.exit(1)

# Create minimal clean content
content = """import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.security import InputValidator, RateLimiter, CircuitBreaker, ComplianceChecker
from core.monitoring import SystemMonitor

@pytest.fixture
def sample_product():
    return {'id': '12345', 'name': 'Test Laptop', 'price': 45000.00}

@pytest.fixture
def system_monitor():
    return SystemMonitor()

@pytest.fixture
def rate_limiter():
    return RateLimiter(max_calls=3, window_seconds=1)

@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(failure_threshold=2, recovery_timeout=1)
"""

# Write as binary (no encoding issues)
with open(filepath, 'wb') as f:
    f.write(content.encode('utf-8'))

print(f"Created: {filepath}")

# Verify it's clean
with open(filepath, 'rb') as f:
    data = f.read()
    if b'\x00' in data:
        print("ERROR: Still has null bytes!")
        sys.exit(1)
    else:
        print(f"Verified clean: {len(data)} bytes, no null bytes")
