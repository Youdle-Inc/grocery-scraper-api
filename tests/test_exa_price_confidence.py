import asyncio
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scraper.exa_structured_client import ExaStructuredClient


class FakeResult:
    def __init__(self, summary: str):
        self.summary = summary
        self.text = ""


class FakeResponse:
    def __init__(self, results):
        self.results = results


class FakeExaClient:
    def __init__(self, response):
        self._response = response

    def get_contents(self, *_args, **_kwargs):
        return self._response


def _make_client_with_summary(summary_payload):
    client = ExaStructuredClient(api_key=None)
    result = FakeResult(summary=json.dumps(summary_payload))
    client._client = FakeExaClient(FakeResponse([result]))
    return client


@pytest.mark.parametrize(
    ("summary_payload", "expected"),
    [
        ({"price": 1.23, "confidence": "low"}, None),
        ({"price": 4.99, "confidence": "Low"}, None),
        ({"price": 4.99, "confidence": " LOW "}, None),
        ({"price": 4.99, "confidence": "low"}, None),
        ({"price": 4.99, "confidence": "medium"}, 4.99),
    ],
)
def test_get_price_from_exa_respects_confidence(summary_payload, expected):
    client = _make_client_with_summary(summary_payload)
    price = asyncio.run(client._get_price_from_exa("https://www.target.com/p/item"))
    assert price == expected


@pytest.mark.parametrize(
    ("summary_payload", "expected"),
    [
        ({"price": 3.49, "confidence": "medium"}, 3.49),
        ({"price": 3.49, "confidence": "low"}, None),
        ({"price": 3.49, "confidence": "high"}, 3.49),
    ],
)
def test_get_price_from_exa_applies_same_confidence_rules_for_wegmans(summary_payload, expected):
    client = _make_client_with_summary(summary_payload)
    price = asyncio.run(client._get_price_from_exa("https://www.wegmans.com/shop/product/59715-Hi-Pro-Ultra-Filtered-Fat-Free-Milk"))
    assert price == expected


@pytest.mark.parametrize(
    "summary_payload",
    [
        {"price": None},
        {},
        {"price": "not-a-number"},
        {"price": 1001},
        {"price": 0},
    ],
)
def test_get_price_from_exa_returns_none_for_unknown_or_invalid_price(summary_payload):
    client = _make_client_with_summary(summary_payload)
    price = asyncio.run(client._get_price_from_exa("https://www.target.com/p/item"))
    assert price is None
