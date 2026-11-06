import sys
import os
from pathlib import Path

# Resolve absolute paths
ROOT_DIR = Path(__file__).resolve().parent
OS_DIR = ROOT_DIR / "os"

# Ensure root and os directories are in sys.path
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(OS_DIR) not in sys.path:
    sys.path.insert(0, str(OS_DIR))

# Import the master platform application from gateway.main (avoiding Python's built-in 'os' collision)
from gateway.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
