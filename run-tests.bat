@echo off
python -m pytest tests -v --cov=core --cov-report=term-missing --cov-fail-under=70
