import sys
sys.path.insert(0, '.')
try:
    import tests.conftest
    print("SUCCESS: conftest imported OK")
except SyntaxError as e:
    print(f"SyntaxError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
