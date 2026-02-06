import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def sample_product():
    return {'id': '12345', 'name': 'Test Laptop', 'price': 45000.00}
