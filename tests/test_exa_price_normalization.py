import asyncio
import json
import pathlib
import sys

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scraper.exa_structured_client import ExaStructuredClient
from scraper.store_extractors import StoreProductExtractor, TargetExtractor, WalmartExtractor, WegmansExtractor


class FakeResult:
    def __init__(self, summary: str, text: str = "", url: str = "https://example.com/product/1", title: str = "Milk"):
        self.summary = summary
        self.text = text
        self.url = url
        self.title = title


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
        ({"price": 4.99, "confidence": "low"}, None),
        ({"price": 4.99, "confidence": "medium"}, 4.99),
    ],
)
def test_get_price_from_exa_respects_confidence(summary_payload, expected):
    client = _make_client_with_summary(summary_payload)
    price = asyncio.run(client._get_price_from_exa("https://www.target.com/p/item"))
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


def test_get_price_from_exa_rejects_bool_price():
    client = _make_client_with_summary({"price": True, "confidence": "medium"})
    price = asyncio.run(client._get_price_from_exa("https://www.target.com/p/item"))
    assert price is None


@pytest.mark.parametrize(
    ("raw_price", "expected"),
    [
        (1.23, 1.23),
        ("1.23", 1.23),
        ("check store", None),
        ("", None),
        (None, None),
        ("not-a-number", None),
        (1001, None),
        (0, None),
    ],
)
def test_convert_summary_to_product_normalizes_price(raw_price, expected):
    client = ExaStructuredClient(api_key=None)
    result = FakeResult(summary="{}", url="https://example.com/product/abc", title="Fallback Name")

    product = client._convert_summary_to_product(
        summary_data={"product_name": "Test Milk", "price": raw_price},
        result=result,
        store_name="Target",
        zipcode="38125",
    )

    assert product is not None
    assert product["price"] == expected


def test_wegmans_extractor_keeps_unknown_price_null():
    extractor = WegmansExtractor()

    from_json_ld = extractor._extract_from_json_ld(
        {"name": "Milk", "offers": {}, "url": "https://www.wegmans.com/shop/product/milk"},
        "wegmans",
    )
    assert from_json_ld is not None
    assert from_json_ld["price"] is None
    assert from_json_ld["price_display"] is None

    from_dict = extractor._extract_from_dict(
        {"name": "Milk", "url": "https://www.wegmans.com/shop/product/milk"},
        "wegmans",
    )
    assert from_dict is not None
    assert from_dict["price"] is None
    assert from_dict["price_display"] is None


def test_wegmans_extract_from_dict_handles_string_price_without_crashing():
    extractor = WegmansExtractor()
    product = extractor._extract_from_dict(
        {"name": "Milk", "price": "4.99", "url": "https://www.wegmans.com/shop/product/milk"},
        "wegmans",
    )
    assert product is not None
    assert product["price"] == 4.99
    assert product["price_display"] == "$4.99"


@pytest.mark.parametrize(
    ("raw_price", "expected"),
    [
        ("check store", None),
        ("unknown", None),
        ("n/a", None),
        ("", None),
        (None, None),
        ("12.34", 12.34),
        (12.34, 12.34),
        (True, None),
        (False, None),
        (1001, None),
    ],
)
def test_store_base_normalize_price_value(raw_price, expected):
    extractor = StoreProductExtractor()
    assert extractor._normalize_price_value(raw_price) == expected


def test_target_extractor_returns_name_only_products_with_null_price():
    extractor = TargetExtractor()
    soup = BeautifulSoup(
        """
        <div>
          <h3 data-test="product-title">Target Milk</h3>
          <a href="/p/milk/-/A-123">View</a>
        </div>
        """,
        "html.parser",
    )
    card = soup.select_one("div")

    product = extractor._extract_product(card, "target")

    assert product is not None
    assert product["name"] == "Milk"
    assert product["price"] is None
    assert product["price_display"] is None


def test_walmart_extractor_returns_name_only_products_with_null_price():
    extractor = WalmartExtractor()
    soup = BeautifulSoup(
        """
        <div data-item-id="abc123">
          <a href="/ip/sample/123" aria-label="Walmart Milk"></a>
        </div>
        """,
        "html.parser",
    )
    item = soup.select_one("div[data-item-id]")

    product = extractor._extract_product(item, "walmart")

    assert product is not None
    assert product["name"] == "Milk"
    assert product["price"] is None
    assert product["price_display"] is None


def test_target_extractor_keeps_valid_price_extraction():
    extractor = TargetExtractor()
    soup = BeautifulSoup(
        """
        <div>
          <h3 data-test="product-title">Target Milk</h3>
          <div data-test="product-price">$4.99</div>
          <a href="/p/milk/-/A-123">View</a>
        </div>
        """,
        "html.parser",
    )
    card = soup.select_one("div")

    product = extractor._extract_product(card, "target")

    assert product is not None
    assert product["price"] == 4.99
    assert product["price_display"] == "$4.99"
