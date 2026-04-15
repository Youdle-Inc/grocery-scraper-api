import asyncio
import json
import pathlib
import sys
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import main
from scraper.location_service import LocationService
from scraper.rate_limit import DEFAULT_ROUTE_LIMITS, RateLimiter, RouteLimit


class FakePartnerAPIClient:
    def has_partner_api(self, store_id: str) -> bool:
        return False

    async def search_products(self, store_id: str, query: str, zipcode: str, limit: int):
        return []


class ConfigurablePartnerAPIClient:
    def __init__(self, stores_with_api=None, products_by_store=None, errors_by_store=None):
        self.stores_with_api = set(stores_with_api or [])
        self.products_by_store = products_by_store or {}
        self.errors_by_store = errors_by_store or {}
        self.calls = []

    def has_partner_api(self, store_id: str) -> bool:
        return store_id in self.stores_with_api

    async def search_products(self, store_id: str, query: str, zipcode: str, limit: int):
        self.calls.append({"store_id": store_id, "query": query, "zipcode": zipcode, "limit": limit})
        if store_id in self.errors_by_store:
            raise RuntimeError(self.errors_by_store[store_id])
        return self.products_by_store.get(store_id, [])


class FakeLocationService:
    def __init__(self, allowed_store_ids=None):
        self.allowed_store_ids = allowed_store_ids

    def _normalize(self, store_id: str) -> str:
        return main._normalize_store_id(store_id)

    def filter_stores_by_location(self, store_ids, zipcode):
        normalized = [self._normalize(store_id) for store_id in store_ids]
        if self.allowed_store_ids is None:
            return normalized
        allowed = {self._normalize(store_id) for store_id in self.allowed_store_ids}
        return [store_id for store_id in normalized if store_id in allowed]

    async def resolve_store_ids_by_location(self, store_ids, zipcode):
        return self.filter_stores_by_location(store_ids, zipcode)


class FakeExaClient:
    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.search_calls = []

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
        self.search_calls.append(
            {
                "query": query,
                "store_name": store_name,
                "zipcode": zipcode,
                "num_results": num_results,
            }
        )
        if self.delay:
            await asyncio.sleep(self.delay)

        return [
            {
                "name": f"{query.title()} Product",
                "brand": store_name,
                "price": 3.99,
                "currency": "USD",
                "quantity": "1 unit",
                "image_url": "https://example.com/image.jpg",
                "product_url": "https://example.com/product",
                "store_name": store_name,
                "store_zipcode": zipcode,
            }
        ]

    async def search_stores_in_zipcode(self, store_chain: str, zipcode: str):
        return [
            {
                "store_id": store_chain.lower().replace(" ", "_"),
                "store_name": f"{store_chain} {zipcode}",
                "address": f"123 Main St, City, ST {zipcode}",
                "services": ["in-store"],
                "status": "active",
                "zipcode": zipcode,
                "city": "City",
                "state": "ST",
            }
        ]


class HangingSearchExaClient:
    def __init__(self):
        self.started = {"target": asyncio.Event(), "walmart": asyncio.Event()}
        self.cancelled = {"target": False, "walmart": False}

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
        self.started[store_id].set()
        try:
            await asyncio.sleep(10)
            return []
        except asyncio.CancelledError:
            self.cancelled[store_id] = True
            raise


def _make_limiter(**overrides):
    policies = dict(DEFAULT_ROUTE_LIMITS)
    policies.update(overrides)
    return RateLimiter(redis_url="", policies=policies)


async def _json_get(client: httpx.AsyncClient, path: str):
    response = await client.get(path)
    return response


async def _collect_sse_events(client: httpx.AsyncClient, path: str):
    events = []
    async with client.stream("GET", path) as response:
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


def test_json_route_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(
        main,
        "rate_limiter",
        _make_limiter(search=RouteLimit(request_limit=1, window_seconds=60)),
    )
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "exa_client", FakeExaClient())

    transport = httpx.ASGITransport(app=main.app)

    async def run():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            first = await _json_get(client, "/products/search?query=milk&zipcode=60601")
            second = await _json_get(client, "/products/search?query=milk&zipcode=60601")
            return first, second

    first, second = asyncio.run(run())

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers.get("retry-after")
    assert second.json()["detail"] == "Rate limit exceeded"


def test_exempt_routes_are_not_throttled(monkeypatch):
    monkeypatch.setattr(
        main,
        "rate_limiter",
        _make_limiter(search=RouteLimit(request_limit=0, window_seconds=60)),
    )

    transport = httpx.ASGITransport(app=main.app)

    async def run():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            results = []
            for path in ["/health", "/api", "/swagger"]:
                results.append(await client.get(path))
                results.append(await client.get(path))
            return results

    results = asyncio.run(run())

    assert all(response.status_code == 200 for response in results)


def test_aggregate_stream_blocks_second_concurrent_request(monkeypatch):
    monkeypatch.setattr(
        main,
        "rate_limiter",
        _make_limiter(
            aggregate_stream=RouteLimit(
                request_limit=10,
                window_seconds=60,
                concurrent_stream_limit=1,
                concurrent_retry_after_seconds=5,
            )
        ),
    )
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "exa_client", FakeExaClient(delay=0.3))

    class FakeRequest:
        headers = {}
        client = SimpleNamespace(host="127.0.0.1")

        async def is_disconnected(self):
            return False

    async def run():
        first_response = await main.aggregate_products_stream(
            request=FakeRequest(),
            query="milk",
            zipcode="38125",
            stores="walmart",
            all_stores=False,
            limit=8,
            store_timeout_s=5,
            overall_timeout_s=10,
        )
        assert first_response.status_code == 200
        with pytest.raises(main.HTTPException) as exc_info:
            await main.aggregate_products_stream(
                request=FakeRequest(),
                query="milk",
                zipcode="38125",
                stores="walmart",
                all_stores=False,
                limit=8,
                store_timeout_s=5,
                overall_timeout_s=10,
            )
        return exc_info.value

    exc = asyncio.run(run())
    assert exc.status_code == 429


def test_search_stream_releases_slot_after_completion(monkeypatch):
    monkeypatch.setattr(
        main,
        "rate_limiter",
        _make_limiter(
            search_stream=RouteLimit(
                request_limit=10,
                window_seconds=60,
                concurrent_stream_limit=1,
                concurrent_retry_after_seconds=5,
            )
        ),
    )
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "exa_client", FakeExaClient())

    transport = httpx.ASGITransport(app=main.app)

    async def run():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            first_events = await _collect_sse_events(
                client,
                "/products/search/stream?query=milk&zipcode=60601&stores=Target&num_results=1",
            )
            second_events = await _collect_sse_events(
                client,
                "/products/search/stream?query=milk&zipcode=60601&stores=Target&num_results=1",
            )
            return first_events, second_events

    first_events, second_events = asyncio.run(run())

    assert first_events[-1]["type"] == "complete"
    assert second_events[-1]["type"] == "complete"


def test_search_products_blocks_store_not_near_zipcode(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", LocationService(google_api_key=""))
    monkeypatch.setattr(main, "exa_client", FakeExaClient())

    transport = httpx.ASGITransport(app=main.app)

    async def run():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/products/search?query=milk&store_name=H-E-B&zipcode=60616")
            return response

    response = asyncio.run(run())

    assert response.status_code == 200
    payload = response.json()
    assert payload["products_found"] == 0
    assert payload["source"] == "location_filtered"


def test_search_products_partner_empty_does_not_fallback_to_exa(monkeypatch):
    partner = ConfigurablePartnerAPIClient(stores_with_api={"target"}, products_by_store={"target": []})
    exa = FakeExaClient()
    monkeypatch.setattr(main, "partner_api_client", partner)
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "exa_client", exa)

    transport = httpx.ASGITransport(app=main.app)

    async def run():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/products/search?query=partner-empty-test&store_name=Target&zipcode=60601&refresh=true"
            )
            return response

    response = asyncio.run(run())

    assert response.status_code == 200
    payload = response.json()
    assert payload["products"] == []
    assert payload["products_found"] == 0
    assert payload["source"] == "partner_api"
    assert len(exa.search_calls) == 0


def test_search_products_partner_error_does_not_fallback_to_exa(monkeypatch):
    partner = ConfigurablePartnerAPIClient(
        stores_with_api={"target"},
        errors_by_store={"target": "partner timeout"},
    )
    exa = FakeExaClient()
    monkeypatch.setattr(main, "partner_api_client", partner)
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "exa_client", exa)

    transport = httpx.ASGITransport(app=main.app)

    async def run():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/products/search?query=partner-error-test&store_name=Target&zipcode=60601&refresh=true"
            )
            return response

    response = asyncio.run(run())

    assert response.status_code == 200
    payload = response.json()
    assert payload["products"] == []
    assert payload["products_found"] == 0
    assert payload["source"] == "partner_api"
    assert len(exa.search_calls) == 0


def test_search_products_non_partner_store_still_uses_exa(monkeypatch):
    partner = ConfigurablePartnerAPIClient(stores_with_api={"target"})
    exa = FakeExaClient()
    monkeypatch.setattr(main, "partner_api_client", partner)
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    monkeypatch.setattr(main, "exa_client", exa)

    transport = httpx.ASGITransport(app=main.app)

    async def run():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/products/search?query=non-partner-fallback-test&store_name=H-E-B&zipcode=60601&refresh=true"
            )
            return response

    response = asyncio.run(run())

    assert response.status_code == 200
    payload = response.json()
    assert payload["products_found"] == 1
    assert payload["source"] == "exa_structured"
    assert len(exa.search_calls) == 1
    assert exa.search_calls[0]["store_name"] == "H-E-B"


def test_stores_endpoint_uses_location_service_and_excludes_unavailable_chain(monkeypatch):
    monkeypatch.setattr(main, "location_service", FakeLocationService(allowed_store_ids=["target", "walmart"]))
    monkeypatch.setattr(main, "exa_client", FakeExaClient())

    transport = httpx.ASGITransport(app=main.app)

    async def run():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/stores/10001")
            return response

    response = asyncio.run(run())

    assert response.status_code == 200
    payload = response.json()
    store_ids = [store["store_id"] for store in payload["stores"]]
    assert "target" in store_ids
    assert "walmart" in store_ids
    assert "kroger" not in store_ids
    assert payload["source"] == "location_service"


def test_search_stream_cancels_inflight_tasks_when_client_disconnects(monkeypatch):
    monkeypatch.setattr(main, "partner_api_client", FakePartnerAPIClient())
    monkeypatch.setattr(main, "location_service", FakeLocationService())
    fake_exa = HangingSearchExaClient()
    monkeypatch.setattr(main, "exa_client", fake_exa)

    async def run():
        class FakeRequest:
            headers = {}

            def __init__(self):
                self.client = SimpleNamespace(host="127.0.0.1")

            async def is_disconnected(self):
                return False

        response = await main.search_products_stream(
            request=FakeRequest(),
            query="milk",
            stores="Target,Walmart",
            zipcode="60601",
            num_results=1,
        )

        agen = response.body_iterator
        start_chunk = await agen.__anext__()
        assert '"type": "start"' in start_chunk
        pending_next = asyncio.create_task(agen.__anext__())
        deadline = asyncio.get_running_loop().time() + 1.0
        while not all(event.is_set() for event in fake_exa.started.values()):
            if asyncio.get_running_loop().time() > deadline:
                raise AssertionError("search tasks did not start")
            await asyncio.sleep(0.01)
        pending_next.cancel()
        try:
            await pending_next
        except asyncio.CancelledError:
            pass
        await agen.aclose()
        await asyncio.sleep(0.1)

    asyncio.run(run())

    assert fake_exa.cancelled["target"] is True
    assert fake_exa.cancelled["walmart"] is True
