"""
Vercel serverless entrypoint for FastAPI.

Expose the ASGI app at module scope so the runtime can detect it reliably.
"""

import main as main_module
from scraper.stream_price_enrichment import install_stream_price_enrichment

install_stream_price_enrichment(main_module)

app = main_module.app

# Some ASGI hosts look for `application` instead of `app`.
application = app
