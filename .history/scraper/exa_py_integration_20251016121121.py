#!/usr/bin/env python3
"""
Thin wrapper around exa_py Exa client to provide Exa-only product search
and image extraction for grocery products.
"""

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

try:
    from exa_py import Exa  # type: ignore
except Exception:  # pragma: no cover - exa-py may be optional in some envs
    Exa = None  # type: ignore


class ExaPyClient:
    """Exa-only client using exa_py SDK."""

    def __init__(self, api_key: Optional[str] = None):
        # Ensure .env is loaded
        load_dotenv()
        self.api_key = api_key or os.environ.get("EXA_API_KEY")
        self._client = Exa(self.api_key) if (Exa and self.api_key) else None

    def is_available(self) -> bool:
        # Lazy init in case env becomes available later
        if self._client is None and Exa and (self.api_key or os.environ.get("EXA_API_KEY")):
            self.api_key = self.api_key or os.environ.get("EXA_API_KEY")
            if self.api_key:
                try:
                    self._client = Exa(self.api_key)
                except Exception:
                    self._client = None
        return self._client is not None

    def search_grocery_products(
        self, query: str, filters: Optional[Dict[str, Any]] = None, num_results: int = 10
    ):
        """
        Advanced grocery product search with filtering and image extraction.
        Returns raw Exa SDK response (results) compatible with extract_product_images.
        """
        if not self.is_available():
            return []

        search_options: Dict[str, Any] = {
            "query": query,
            "numResults": num_results,
            "type": "auto",
        }

        grocery_domains = [
            "walmart.com",
            "kroger.com",
            "wholefoodsmarket.com",
            "instacart.com",
        ]
        search_options["includeDomains"] = grocery_domains

        if filters and filters.get("organic"):
            search_options["includeText"] = ["organic"]

        response = self._client.search_and_contents(  # type: ignore[attr-defined]
            **search_options,
            text={"max_characters": 1000},
            summary={
                "query": "Extract product name, price, availability, and nutritional info",
                "schema": {
                    "type": "object",
                    "properties": {
                        "product_name": {"type": "string"},
                        "price": {"type": "string"},
                        "availability": {"type": "string"},
                        "nutrition": {"type": "object"},
                        "image_url": {"type": "string"},
                    },
                },
            },
            extras={"imageLinks": 3},
        )

        processed_results = []
        for result in getattr(response, "results", []) or []:
            if hasattr(result, "summary") and isinstance(result.summary, dict):
                if not result.summary.get("image_url") and getattr(result, "image", None):
                    result.summary["image_url"] = result.image
            processed_results.append(result)

        return processed_results

    @staticmethod
    def extract_product_images(results) -> List[Dict[str, Any]]:
        """Extract and process product images from Exa search results."""
        products: List[Dict[str, Any]] = []

        for result in results or []:
            details = result.summary if hasattr(result, "summary") else {}
            product: Dict[str, Any] = {
                "title": getattr(result, "title", None),
                "url": getattr(result, "url", None),
                "details": details if isinstance(details, dict) else {},
            }

            if getattr(result, "image", None):
                product["image_url"] = result.image
            elif hasattr(result, "extras") and getattr(result, "extras", None) and "imageLinks" in result.extras:
                product_images = [
                    img for img in result.extras["imageLinks"] if isinstance(img, str) and ("product" in img.lower() or "item" in img.lower())
                ]
                if product_images:
                    product["image_url"] = product_images[0]
                    if len(product_images) > 1:
                        product["additional_images"] = product_images[1:3]

            products.append(product)

        return products


