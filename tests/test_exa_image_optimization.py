import asyncio
import json
import pathlib
import sys
from typing import Optional

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import main
import scraper.exa_structured_client as exa_module
from scraper.exa_structured_client import ExaStructuredClient


class FakeResult:
    def __init__(self, url: str, title: str, summary: str, image: Optional[str] = None):
        self.url = url
        self.title = title
        self.summary = summary
        self.text = ""
        if image is not None:
            self.image = image


class FakeSearchExaClient:
    def __init__(self, products):
        self.products = products

    def is_available(self):
        return True

    async def search_products_structured(
        self,
        query,
        store_name,
        zipcode,
        num_results,
        include_location=False,
        context=None,
    ):
        return [dict(product) for product in self.products]


class FakeImageCache:
    async def cache_images_batch(self, products):
        return None


async def _search_get(path: str):
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path)


def test_convert_summary_to_product_preserves_result_image():
    client = ExaStructuredClient(api_key=None)
    result = FakeResult(
        url="https://example.com/product/123",
        title="Organic Milk",
        summary=json.dumps({"product_name": "Organic Milk", "confidence_score": 0.95}),
        image="https://example.com/image.jpg",
    )

    product = client._convert_summary_to_product(
        {"product_name": "Organic Milk", "confidence_score": 0.95},
        result,
        "Target",
        "38125",
    )

    assert product is not None
    assert product["image_url"] == "https://example.com/image.jpg"


def test_process_single_result_keeps_missing_image_missing(monkeypatch):
    client = ExaStructuredClient(api_key=None)
    monkeypatch.setattr(exa_module, "_image_cache", None)

    result = FakeResult(
        url="https://example.com/product/456",
        title="Organic Milk",
        summary=json.dumps({"product_name": "Organic Milk", "confidence_score": 0.95}),
    )

    product = asyncio.run(
        client._process_single_result(
            result=result,
            store_name="Target",
            zipcode="38125",
            query="milk",
            idx=0,
        )
    )

    assert product is not None
    assert product["name"] == "Organic Milk"
    assert product.get("image_url") is None


def test_search_response_keeps_upstream_image_and_hides_image_source(monkeypatch):
    monkeypatch.setattr(main, "cache", None)
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeSearchExaClient(
            [
                {
                    "name": "Organic Milk",
                    "brand": "Target",
                    "price": 3.99,
                    "currency": "USD",
                    "quantity": "64 oz",
                    "image_url": "https://example.com/upstream.jpg",
                    "product_url": "https://example.com/product/1",
                    "_image_source": "search_supplied",
                }
            ]
        ),
    )
    monkeypatch.setattr(main, "image_cache", FakeImageCache())
    monkeypatch.setattr(main, "partner_api_client", None)
    monkeypatch.setattr(main, "location_service", None)
    monkeypatch.setattr(main, "web_search_service", None)

    response = asyncio.run(_search_get("/products/search?query=milk&store_name=Target&num_results=10"))

    assert response.status_code == 200
    payload = response.json()
    product = payload["products"][0]

    assert product["image_url"] == "https://example.com/upstream.jpg"
    assert "_image_source" not in product


def test_search_response_keeps_cached_image_and_hides_image_source(monkeypatch):
    monkeypatch.setattr(main, "cache", None)
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeSearchExaClient(
            [
                {
                    "name": "Organic Milk",
                    "brand": "Target",
                    "price": 3.99,
                    "currency": "USD",
                    "quantity": "64 oz",
                    "image_url": "https://example.com/cached.jpg",
                    "product_url": "https://example.com/product/2",
                    "_image_source": "cache",
                }
            ]
        ),
    )
    monkeypatch.setattr(main, "image_cache", FakeImageCache())
    monkeypatch.setattr(main, "partner_api_client", None)
    monkeypatch.setattr(main, "location_service", None)
    monkeypatch.setattr(main, "web_search_service", None)

    response = asyncio.run(_search_get("/products/search?query=milk&store_name=Target&num_results=10"))

    assert response.status_code == 200
    payload = response.json()
    product = payload["products"][0]

    assert product["image_url"] == "https://example.com/cached.jpg"
    assert "_image_source" not in product


def test_log_image_coverage_does_not_mutate_products():
    products = [
        {"name": "Organic Milk", "image_url": "https://example.com/milk.jpg", "_image_source": "cache"},
        {"name": "Eggs", "image_url": None, "_image_source": "search_supplied"},
    ]

    main._log_image_coverage(products, "test-context")

    assert products[0]["_image_source"] == "cache"
    assert products[1]["_image_source"] == "search_supplied"
