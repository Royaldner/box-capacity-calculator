"""
Run the BBX Packer API server.

Usage:
    python run_server.py

Server starts at http://localhost:8000
API docs at http://localhost:8000/docs
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "bbx_packer.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only)
    )
