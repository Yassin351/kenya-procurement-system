@echo off
cd /d "C:\Users\STUDENTS\Desktop\exam rag system\kenya-procurement-system"
del /f tests\conftest.py 2>nul
echo import pytest > tests\conftest.py
echo import sys >> tests\conftest.py
echo import os >> tests\conftest.py
echo. >> tests\conftest.py
echo sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) >> tests\conftest.py
echo. >> tests\conftest.py
echo from core.security import InputValidator, RateLimiter, CircuitBreaker, ComplianceChecker >> tests\conftest.py
echo from core.monitoring import SystemMonitor >> tests\conftest.py
echo. >> tests\conftest.py
echo @pytest.fixture >> tests\conftest.py
echo def sample_product(): >> tests\conftest.py
echo     return {'id': '12345', 'name': 'Test Laptop', 'price': 45000.00} >> tests\conftest.py
echo. >> tests\conftest.py
echo @pytest.fixture >> tests\conftest.py
echo def system_monitor(): >> tests\conftest.py
echo     return SystemMonitor() >> tests\conftest.py
echo. >> tests\conftest.py
echo @pytest.fixture >> tests\conftest.py
echo def rate_limiter(): >> tests\conftest.py
echo     return RateLimiter(max_calls=3, window_seconds=1) >> tests\conftest.py
echo. >> tests\conftest.py
echo @pytest.fixture >> tests\conftest.py
echo def circuit_breaker(): >> tests\conftest.py
echo     return CircuitBreaker(failure_threshold=2, recovery_timeout=1) >> tests\conftest.py
