#!/usr/bin/env python
# run_async.py
import os
import sys

# Set environment for async
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

# Add project to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    # Run with uvicorn for full async support
    import uvicorn
    
    uvicorn.run(
        "config.asgi:application",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )