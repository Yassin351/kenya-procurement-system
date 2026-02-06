import sys
import os

# Check each file in tests
test_files = ['tests/__init__.py', 'tests/conftest.py']

for filepath in test_files:
    print(f"\nChecking {filepath}...")
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
            if b'\x00' in data:
                print(f"  ERROR: Contains null bytes at positions: {[i for i, b in enumerate(data) if b == 0]}")
            else:
                print(f"  OK: {len(data)} bytes, no null bytes")
    except Exception as e:
        print(f"  Error reading: {e}")

# Now check core module files
core_files = []
for root, dirs, files in os.walk('core'):
    for f in files:
        if f.endswith('.py'):
            core_files.append(os.path.join(root, f))

print(f"\nChecking {len(core_files)} files in core...")
for filepath in sorted(core_files):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
            if b'\x00' in data:
                print(f"  ERROR in {filepath}: Contains null bytes")
            else:
                print(f"  OK: {filepath}")
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
