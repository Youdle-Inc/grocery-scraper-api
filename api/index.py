"""
Vercel serverless entrypoint for FastAPI.

Vercel's Python runtime detects ASGI apps when a module-level variable named
`app` is exposed. We re-export the FastAPI `app` from `main.py`.
"""

from main import app as app  # noqa: F401


