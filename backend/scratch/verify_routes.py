import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    from app.main import app
    print("✓ App imported successfully")
    print(f"\n{len(app.routes)} routes registered:\n")
    for r in app.routes:
        if hasattr(r, 'path'):
            print(f"  {r.path}")
except Exception as e:
    import traceback
    print("✗ Import failed:")
    traceback.print_exc()
