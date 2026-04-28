import asyncio
import copy
import pathlib
import sys
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import main


class FakePartnerAPIClient:
    target_client = None
    kroger_client = None

    def has_partner_api(self, _store_id: str) -> bool:
        return False

    async def search_products(self, store_id: str, query: str, zipcode: str, limit: int):
        return []


class FakeLocationService:
    google_api_key = None

    def filter_stores_by_location(self, store_ids, zipcode):
        return [main._normalize_store_id(store_id) for store_id in store_ids]

    async def resolve_store_ids_by_location(self, store_ids, zipcode):
        return self.filter_stores_by_location(store_ids, zipcode)


class FakeGeocodingService:
    async def get_location_from_zipcode(self, zipcode: str):
        return ("Memphis", "TN", 35.0424, -89.9342)


class FakeExaClient:
    def __init__(self, products_by_store_id):
        self.products_by_store_id = products_by_store_id

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
        store_id = main._normalize_store_id(store_name)
        return copy.deepcopy(self.products_by_store_id.get(store_id, []))

    async def search_stores_in_zipcode(self, store_chain: str, zipcode: str):
        store_id = main._normalize_store_id(store_chain)
        return [
            {
                "store_id": store_id,
                "retailer_store_id": f"{store_id}-1",
                "store_name": store_chain,
                "address": f"123 Main St, City, ST {zipcode}",
                "city": "City",
                "state": "ST",
                "zipcode": zipcode,
            }
        ]


async def _aggregate_get(path: str):
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path)


def _configure_dependencies(monkeypatch, exa_client):
    monkeypatch.setattr(main, "cache", None)
    monkeypatch.setattr(main, "exa_client", exa_client)
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "ai_scraper", SimpleNamespace(is_available=lambda: False))
    monkeypatch.setattr(main, "web_search_service", None)
    monkeypatch.setattr(main, "get_geocoding_service", lambda: FakeGeocodingService())


def test_aggregate_keeps_existing_upstream_images(monkeypatch):
    exa_client = FakeExaClient(
        {
            "target": [
                {
                    "name": "Organic Milk",
                    "brand": "Target",
                    "price": 3.99,
                    "currency": "USD",
                    "quantity": "64 oz",
                    "image_url": "https://example.com/target-milk.jpg",
                    "product_url": "https://www.target.com/p/milk/A-123",
                    "store_name": "Target",
                    "store_zipcode": "38125",
                }
            ]
        }
    )
    _configure_dependencies(monkeypatch, exa_client)

    response = asyncio.run(
        _aggregate_get("/products/aggregate?query=milk&zipcode=38125&stores=target&limit=10")
    )

    assert response.status_code == 200
    payload = response.json()
    result = payload["results"][0]

    assert result["images"] == [
        {"url": "https://example.com/target-milk.jpg", "is_primary": True}
    ]
    assert result["offers"][0]["product_url"] == "https://www.target.com/p/milk/A-123"


def test_aggregate_filters_wegmans_logo_images(monkeypatch):
    exa_client = FakeExaClient(
        {
            "wegmans": [
                {
                    "name": "Wegmans Milk",
                    "brand": "Wegmans",
                    "price": 2.99,
                    "currency": "USD",
                    "quantity": "1 gal",
                    "image_url": "https://assets.wegmans.com/wegmans-og-share-img-53100.jpg",
                    "product_url": "https://www.wegmans.com/shop/product/12345/milk",
                    "store_name": "Wegmans",
                    "store_zipcode": "38125",
                }
            ]
        }
    )
    _configure_dependencies(monkeypatch, exa_client)

    response = asyncio.run(
        _aggregate_get("/products/aggregate?query=milk&zipcode=38125&stores=wegmans&limit=10")
    )

    assert response.status_code == 200
    payload = response.json()
    result = payload["results"][0]

    assert result["images"] == []


def test_aggregate_keeps_missing_images_missing(monkeypatch):
    exa_client = FakeExaClient(
        {
            "target": [
                {
                    "name": "Store Brand Eggs",
                    "brand": "Target",
                    "price": 2.49,
                    "currency": "USD",
                    "quantity": "12 ct",
                    "image_url": None,
                    "product_url": "https://www.target.com/p/eggs/A-456",
                    "store_name": "Target",
                    "store_zipcode": "38125",
                }
            ]
        }
    )
    _configure_dependencies(monkeypatch, exa_client)

    response = asyncio.run(
        _aggregate_get("/products/aggregate?query=eggs&zipcode=38125&stores=target&limit=10")
    )

    assert response.status_code == 200
    payload = response.json()
    result = payload["results"][0]

    assert result["images"] == []
