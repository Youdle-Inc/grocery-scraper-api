"""
Vercel serverless entrypoint for FastAPI.

Vercel's Python runtime detects ASGI apps when a module-level variable named
`app` is exposed. We re-export the FastAPI `app` from `main.py`.
"""

import logging
import sys

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from main import app as app  # noqa: F401
    logger.info("✅ Successfully imported FastAPI app")
except Exception as e:
    logger.error(f"❌ Failed to import app: {e}", exc_info=True)
    # Create a minimal error app to prevent complete failure
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/health")
    def health():
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to initialize application"
        }
    
    @app.get("/{path:path}")
    def error_handler(path: str):
        return {
            "error": "Application initialization failed",
            "details": str(e)
        }







