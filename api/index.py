"""
Vercel serverless entrypoint for FastAPI.

Expose the ASGI app at module scope so the runtime can detect it reliably.
"""

from main import app

# Some ASGI hosts look for `application` instead of `app`.
application = app
