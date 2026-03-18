import asyncio
import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import main


class FakePartnerAPIClient:
    def has_partner_api(self, store_id: str) -> bool:
        return False

    async def search_products(self, store_id: str, query: str, zipcode: str, limit: int):
        return []


class FakeLocationService:
    def __init__(self, allowed_store_ids=None):
        self.allowed_store_ids = allowed_store_ids

    def filter_stores_by_location(self, store_ids, zipcode):
        if self.allowed_store_ids is None:
            return list(store_ids)
        allowed = set(self.allowed_store_ids)
        return [store_id for store_id in store_ids if store_id in allowed]


class FakeExaClient:
    def __init__(self, behavior_by_store_id):
        self.behavior_by_store_id = behavior_by_store_id

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
                "target": {"delay": 0.02, "products": [_make_product("target")]},
                "walmart": {"delay": 0.30, "products": [_make_product("walmart")]},
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

    assert any(e["type"] == "error" and e["store"] == "Target" for e in events)
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
