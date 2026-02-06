#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create a clean conftest.py file without corruptions."""

import os

filepath = 'tests/conftest.py'

# Delete if exists
if os.path.exists(filepath):
    os.remove(filepath)
    print(f"Deleted old: {filepath}")

# Create content with proper encoding
content = """import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def sample_product():
    return {'id': '12345', 'name': 'Test Laptop', 'price': 45000.00}
"""

# Write as binary UTF-8
with open(filepath, 'wb') as f:
    f.write(content.encode('utf-8'))

print(f"Created: {filepath}")

# Verify no null bytes
with open(filepath, 'rb') as f:
    data = f.read()
    if b'\x00' in data:
        print("ERROR: Still has null bytes!")
        os.remove(filepath)
        exit(1)
    else:
        print(f"SUCCESS: Clean file, {len(data)} bytes, no null bytes")
