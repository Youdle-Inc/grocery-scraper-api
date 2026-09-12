"""Price enrichment for aggregate streaming product results.

The regular /products/search path verifies missing prices with WebSearchService,
but the aggregate streaming path historically returned the raw product payload
without that verification step. This module keeps the streaming path aligned
without changing its SSE contract.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _coerce_positive_price(value: Any) -> Optional[float]:
    """Return a positive numeric price when one can be safely parsed."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if numeric > 0 else None

    if isinstance(value, str):
        cleaned = value.strip().replace("$", "").replace(",", "")
        if not cleaned:
            return None
        try:
            numeric = float(cleaned)
        except ValueError:
            return None
        return numeric if numeric > 0 else None

    return None


async def enrich_stream_products_with_prices(
    products: List[Dict[str, Any]],
    web_search_service: Any,
) -> List[Dict[str, Any]]:
    """Normalize existing prices and verify missing ones when possible.

    WebSearchService.batch_verify_prices mutates the dictionaries it receives,
    so the original product list is enriched in place and then returned.
    Failures are deliberately non-fatal: a product may still be useful even
    when a price cannot be verified.
    """
    if not products:
        return products

    missing_price_products: List[Dict[str, Any]] = []

    for product in products:
        parsed_price = _coerce_positive_price(product.get("price"))
        if parsed_price is not None:
            product["price"] = parsed_price
            continue

        # A verifier needs a real product page. Products without one remain
        # price-unavailable instead of receiving a guessed value.
        if product.get("product_url"):
            missing_price_products.append(product)

    if not missing_price_products or web_search_service is None:
        return products

    try:
        await web_search_service.batch_verify_prices(missing_price_products)
    except Exception as exc:
        logger.warning("Streaming price verification failed: %s", exc)
        return products

    # Normalize verified values too, so the frontend receives the same numeric
    # shape regardless of whether the price came from a partner API or Exa.
    for product in missing_price_products:
        parsed_price = _coerce_positive_price(product.get("price"))
        if parsed_price is not None:
            product["price"] = parsed_price

    return products


def install_stream_price_enrichment(main_module: Any) -> None:
    """Wrap main._fetch_store_products_for_stream with missing-price verification.

    Vercel imports api/index.py as the production ASGI entrypoint. Installing
    the wrapper there keeps the existing aggregate-stream endpoint and event
    contract intact while restoring the price-verification behavior already
    used by /products/search.
    """
    original_fetch = getattr(main_module, "_fetch_store_products_for_stream", None)
    if not callable(original_fetch):
        logger.warning("Aggregate stream fetch helper was not found; price enrichment not installed")
        return

    if getattr(original_fetch, "_youdle_price_enrichment_installed", False):
        return

    async def fetch_with_price_enrichment(
        store_id: str,
        query: str,
        zipcode: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        products = await original_fetch(store_id, query, zipcode, limit)
        return await enrich_stream_products_with_prices(
            products,
            getattr(main_module, "web_search_service", None),
        )

    fetch_with_price_enrichment._youdle_price_enrichment_installed = True  # type: ignore[attr-defined]
    main_module._fetch_store_products_for_stream = fetch_with_price_enrichment
