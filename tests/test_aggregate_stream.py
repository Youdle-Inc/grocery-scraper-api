import asyncio
import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import main
from scraper.rate_limit import DEFAULT_ROUTE_LIMITS, RateLimiter, RouteLimit

main.rate_limiter = RateLimiter(
    redis_url="",
    policies={
        **DEFAULT_ROUTE_LIMITS,
        "aggregate_stream": RouteLimit(
            request_limit=1000,
            window_seconds=60,
            concurrent_stream_limit=10,
            concurrent_retry_after_seconds=1,
        ),
    },
)


class FakePartnerAPIClient:
    def has_partner_api(self, store_id: str) -> bool:
        return False

    async def search_products(self, store_id: str, query: str, zipcode: str, limit: int):
        return []


class FakeLocationService:
    def __init__(self, allowed_store_ids=None):
        self.allowed_store_ids = allowed_store_ids

    def _normalize(self, store_id: str) -> str:
        return main._normalize_store_id(store_id)

    def filter_stores_by_location(self, store_ids, zipcode):
        if self.allowed_store_ids is None:
            return [self._normalize(store_id) for store_id in store_ids]
        allowed = {self._normalize(store_id) for store_id in self.allowed_store_ids}
        return [self._normalize(store_id) for store_id in store_ids if self._normalize(store_id) in allowed]

    async def resolve_store_ids_by_location(self, store_ids, zipcode):
        return self.filter_stores_by_location(store_ids, zipcode)


class FakeExaClient:
    def __init__(self, behavior_by_store_id, image_results=None):
        self.behavior_by_store_id = behavior_by_store_id
        self.image_results = image_results or {}

    def is_available(self):
        return True

    async def search_products_structured(self, query, store_name, zipcode, num_results, include_location=False, context=None):
        store_id = main._normalize_store_id(store_name)
        behavior = self.behavior_by_store_id.get(store_id, {})

        delay = behavior.get("delay", 0)
        if delay:
            await asyncio.sleep(delay)

        error = behavior.get("error")
        if error:
            raise RuntimeError(error)

        return behavior.get("products", [])

    async def get_product_images_batch(self, product_urls, max_concurrent=5):
        return {url: self.image_results.get(url) for url in product_urls}


class FakeWebSearchService:
    def __init__(self, price_by_url):
        self.price_by_url = price_by_url

    async def batch_verify_prices(self, products):
        verified = []
        for product in products:
            product_url = product.get("product_url")
            verified.append(
                {
                    "product_url": product_url,
                    "price": self.price_by_url.get(product_url),
                }
            )
        return verified


class FakeHTMLImageExtractor:
    def __init__(self, image_by_url):
        self.image_by_url = image_by_url

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def extract_images_batch(self, product_urls, max_concurrent=10):
        return {url: self.image_by_url.get(url) for url in product_urls}


def _make_product(store_id: str, suffix: str = "1"):
    return {
        "name": f"Milk {suffix}",
        "brand": "Brand",
        "price": 3.99,
        "currency": "USD",
        "quantity": "1 gal",
        "image_url": f"https://example.com/{store_id}/{suffix}.jpg",
        "product_url": f"https://example.com/{store_id}/{suffix}",
    }


def _make_product_with_availability(store_id: str, availability: str):
    product = _make_product(store_id)
    product["availability"] = availability
    return product


async def _collect_stream_events(url: str):
    events = []
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with client.stream("GET", url) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    events.append(payload)
                    if payload.get("type") == "complete":
                        break
    return events


def test_stream_emits_fast_store_before_slow_store(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeExaClient(
            {
                "target": {"delay": 0.02, "products": [_make_product_with_availability("target", "In Stock")]},
                "walmart": {"delay": 0.30, "products": [_make_product_with_availability("walmart", "Limited Stock")]},
            }
        ),
    )

    events = asyncio.run(
        _collect_stream_events(
        "/products/aggregate/stream?query=milk&zipcode=38125&stores=target,walmart&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    store_events = [e for e in events if e["type"] == "store_products"]
    assert len(store_events) == 2
    assert store_events[0]["store_id"] == "target"
    assert store_events[1]["store_id"] == "walmart"
    assert store_events[0]["products"][0]["availability"] == "IN_STOCK"
    assert store_events[1]["products"][0]["availability"] == "LOW_STOCK"
    assert events[-1]["type"] == "complete"


def test_stream_continues_after_single_store_failure(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeExaClient(
            {
                "target": {"delay": 0.02, "error": "target failed"},
                "walmart": {"delay": 0.05, "products": [_make_product("walmart")]},
            }
        ),
    )

    events = asyncio.run(
        _collect_stream_events(
        "/products/aggregate/stream?query=milk&zipcode=38125&stores=target,walmart&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    target_errors = [e for e in events if e["type"] == "error" and e["store"] == "Target"]
    assert len(target_errors) == 1
    assert target_errors[0]["error"] == main._STREAM_GENERIC_STORE_ERROR_MESSAGE
    assert any(e["type"] == "store_products" and e["store_id"] == "walmart" for e in events)
    assert events[-1]["type"] == "complete"


def test_stream_per_store_timeout_returns_partial_results(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeExaClient(
            {
                "walmart": {"delay": 0.02, "products": [_make_product("walmart")]},
                "target": {"delay": 2.0, "products": [_make_product("target")]},
            }
        ),
    )

    events = asyncio.run(
        _collect_stream_events(
        "/products/aggregate/stream?query=milk&zipcode=38125&stores=walmart,target&store_timeout_s=1&overall_timeout_s=10",
        )
    )

    assert any(e["type"] == "store_products" and e["store_id"] == "walmart" for e in events)
    assert any(e["type"] == "error" and e["store"] == "Target" and "timed out" in e["error"] for e in events)
    complete = [e for e in events if e["type"] == "complete"]
    assert len(complete) == 1
    assert complete[0]["total_products"] == 1


def test_stream_overall_timeout_ends_with_partial_results(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeExaClient(
            {
                "walmart": {"delay": 0.02, "products": [_make_product("walmart")]},
                "target": {"delay": 3.0, "products": [_make_product("target")]},
            }
        ),
    )

    events = asyncio.run(
        _collect_stream_events(
        "/products/aggregate/stream?query=milk&zipcode=38125&stores=walmart,target&store_timeout_s=10&overall_timeout_s=1",
        )
    )

    assert any(e["type"] == "store_products" and e["store_id"] == "walmart" for e in events)
    assert any(
        e["type"] == "error" and e["store"] == "Target" and "overall timeout" in e["error"]
        for e in events
    )
    complete = [e for e in events if e["type"] == "complete"]
    assert len(complete) == 1
    assert complete[0]["total_products"] == 1


def test_stream_emits_single_complete_with_zipcode(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeExaClient(
            {
                "walmart": {"delay": 0.02, "products": [_make_product("walmart")]},
                "target": {"delay": 0.02, "products": [_make_product("target")]},
            }
        ),
    )

    events = asyncio.run(
        _collect_stream_events(
        "/products/aggregate/stream?query=milk&zipcode=60601&stores=walmart,target&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    complete_events = [e for e in events if e["type"] == "complete"]
    assert len(complete_events) == 1
    assert complete_events[0]["zipcode"] == "60601"


def test_all_stores_overrides_stores_and_caps_to_15(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "exa_client", FakeExaClient({}))

    events = asyncio.run(
        _collect_stream_events(
        "/products/aggregate/stream?query=milk&zipcode=38125&stores=target&all_stores=true&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    start = events[0]
    assert start["type"] == "start"
    assert "walmart" in start["stores"]
    assert len(start["stores"]) == 15


def test_resolve_aggregate_stream_store_ids_returns_empty_when_location_filters_everything(monkeypatch):
    monkeypatch.setattr(main, "location_service", FakeLocationService(allowed_store_ids=[]))

    store_ids = asyncio.run(
        main._resolve_aggregate_stream_store_ids(
            stores="target,walmart",
            all_stores=False,
            zipcode="38125",
        )
    )

    assert store_ids == []


def test_resolve_aggregate_stream_store_ids_falls_back_when_location_service_missing(monkeypatch):
    monkeypatch.setattr(main, "location_service", None)

    store_ids = asyncio.run(
        main._resolve_aggregate_stream_store_ids(
            stores="Target,Walmart",
            all_stores=False,
            zipcode="38125",
        )
    )

    assert store_ids == ["target", "walmart"]


def test_stream_start_only_includes_nearby_stores(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService(allowed_store_ids=["target"]))
    monkeypatch.setattr(main, "exa_client", FakeExaClient({}))

    events = asyncio.run(
        _collect_stream_events(
            "/products/aggregate/stream?query=milk&zipcode=60601&stores=target,heb&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    start_events = [e for e in events if e["type"] == "start"]
    assert len(start_events) == 1
    assert start_events[0]["stores"] == ["target"]


def test_stream_verifies_missing_prices_before_emit(monkeypatch):
    product = _make_product("target")
    product_url = product["product_url"]
    product["price"] = None

    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "web_search_service", FakeWebSearchService({product_url: 4.29}))
    monkeypatch.setattr(main, "exa_client", FakeExaClient({"target": {"products": [product]}}))

    events = asyncio.run(
        _collect_stream_events(
            "/products/aggregate/stream?query=milk&zipcode=38125&stores=target&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    store_events = [e for e in events if e["type"] == "store_products"]
    assert len(store_events) == 1
    assert store_events[0]["products"][0]["price"] == 4.29


def test_stream_enriches_images_via_exa_batch(monkeypatch):
    product = _make_product("target")
    product_url = product["product_url"]
    product["image_url"] = None
    enriched_image = "https://cdn.example.com/target/enriched.jpg"

    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "web_search_service", None)
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeExaClient({"target": {"products": [product]}}, image_results={product_url: enriched_image}),
    )

    events = asyncio.run(
        _collect_stream_events(
            "/products/aggregate/stream?query=milk&zipcode=38125&stores=target&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    store_events = [e for e in events if e["type"] == "store_products"]
    assert len(store_events) == 1
    assert store_events[0]["products"][0]["image_url"] == enriched_image


def test_stream_enriches_images_via_html_fallback_when_exa_misses(monkeypatch):
    product = _make_product("target")
    product_url = product["product_url"]
    product["image_url"] = None
    fallback_image = "https://cdn.example.com/target/html-fallback.jpg"

    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "web_search_service", None)
    monkeypatch.setattr(main, "ai_scraper", None)
    monkeypatch.setattr(main, "HTMLImageExtractor", lambda: FakeHTMLImageExtractor({product_url: fallback_image}))
    monkeypatch.setattr(main, "exa_client", FakeExaClient({"target": {"products": [product]}}, image_results={}))

    events = asyncio.run(
        _collect_stream_events(
            "/products/aggregate/stream?query=milk&zipcode=38125&stores=target&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    store_events = [e for e in events if e["type"] == "store_products"]
    assert len(store_events) == 1
    assert store_events[0]["products"][0]["image_url"] == fallback_image


def test_stream_enrichment_timeouts_fail_open(monkeypatch):
    product = _make_product("target")
    product["price"] = None
    product["image_url"] = None

    async def slow_price_verification(products, store_name):
        await asyncio.sleep(0.05)

    async def slow_image_enrichment(products, store_name):
        await asyncio.sleep(0.05)

    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "exa_client", FakeExaClient({"target": {"products": [product]}}))
    monkeypatch.setattr(main, "_verify_stream_product_prices", slow_price_verification)
    monkeypatch.setattr(main, "_enrich_stream_product_images", slow_image_enrichment)
    monkeypatch.setattr(main, "_STREAM_PRICE_VERIFY_TIMEOUT_S", 0.01)
    monkeypatch.setattr(main, "_STREAM_IMAGE_ENRICH_TIMEOUT_S", 0.01)

    events = asyncio.run(
        _collect_stream_events(
            "/products/aggregate/stream?query=milk&zipcode=38125&stores=target&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    assert any(e["type"] == "store_products" and e["store_id"] == "target" for e in events)
    assert any(e["type"] == "complete" for e in events)


def test_helper_cancels_inflight_tasks_on_disconnect(monkeypatch):
    monkeypatch.setattr(main, "location_service", FakeLocationService())

    cancelled = {"walmart": False, "target": False}

    async def slow_fetch(store_id: str, query: str, zipcode: str, limit: int):
        try:
            await asyncio.sleep(5)
            return []
        except asyncio.CancelledError:
            cancelled[store_id] = True
            raise

    disconnect_checks = {"count": 0}

    async def fake_is_disconnected() -> bool:
        disconnect_checks["count"] += 1
        return disconnect_checks["count"] >= 2

    async def consume():
        chunks = []
        async for chunk in main._stream_aggregate_sse_events(
            query="milk",
            zipcode="38125",
            stores="walmart,target",
            all_stores=False,
            limit=3,
            store_timeout_s=30,
            overall_timeout_s=30,
            is_disconnected_fn=fake_is_disconnected,
            fetch_store_products_fn=slow_fetch,
            keepalive_interval_s=0.01,
        ):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(consume())
    assert any('"type": "start"' in chunk for chunk in chunks)
    assert not any('"type": "complete"' in chunk for chunk in chunks)
    assert cancelled["walmart"] is True
    assert cancelled["target"] is True


def test_stream_sanitizes_unexpected_errors(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(
        main,
        "exa_client",
        FakeExaClient(
            {
                "target": {"delay": 0.01, "error": "internal failure: secret token leaked"},
                "walmart": {"delay": 0.01, "products": [_make_product("walmart")]},
            }
        ),
    )

    events = asyncio.run(
        _collect_stream_events(
        "/products/aggregate/stream?query=milk&zipcode=38125&stores=target,walmart&store_timeout_s=5&overall_timeout_s=10",
        )
    )

    target_errors = [e for e in events if e["type"] == "error" and e["store"] == "Target"]
    assert len(target_errors) == 1
    assert target_errors[0]["error"] == main._STREAM_GENERIC_STORE_ERROR_MESSAGE
    assert "secret token leaked" not in target_errors[0]["error"]


def test_stream_limits_inflight_store_searches_to_five(monkeypatch):
    monkeypatch.setattr(main, "location_service", FakeLocationService())

    in_flight = {"count": 0}
    max_in_flight = {"count": 0}

    async def tracked_fetch(store_id: str, query: str, zipcode: str, limit: int):
        in_flight["count"] += 1
        max_in_flight["count"] = max(max_in_flight["count"], in_flight["count"])
        try:
            await asyncio.sleep(0.05)
            return [_make_product(store_id)]
        finally:
            in_flight["count"] -= 1

    async def consume():
        chunks = []
        async for chunk in main._stream_aggregate_sse_events(
            query="milk",
            zipcode="38125",
            stores=None,
            all_stores=True,
            limit=2,
            store_timeout_s=10,
            overall_timeout_s=30,
            fetch_store_products_fn=tracked_fetch,
            keepalive_interval_s=0.01,
        ):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(consume())

    assert any('"type": "complete"' in chunk for chunk in chunks)
    assert max_in_flight["count"] == main._STREAM_MAX_IN_FLIGHT_STORE_SEARCHES
