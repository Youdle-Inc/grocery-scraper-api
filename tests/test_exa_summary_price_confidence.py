import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scraper.exa_structured_client import ExaStructuredClient


class FakeResult:
    def __init__(self, url: str, title: str):
        self.url = url
        self.title = title


def _convert_summary(summary_payload):
    client = ExaStructuredClient(api_key=None)
    result = FakeResult(
        url="https://www.wegmans.com/shop/product/59715-Hi-Pro-Ultra-Filtered-Fat-Free-Milk",
        title="Wegmans Milk",
    )
    return client._convert_summary_to_product(
        summary_payload,
        result,
        store_name="Wegmans",
        zipcode="14610",
    )


@pytest.mark.parametrize(
    "summary_payload",
    [
        {"product_name": "Milk", "price": 1.23},
        {"product_name": "Milk", "price": 1.23, "confidence_score": 0.79},
        {"product_name": "Milk", "price": "not-a-number", "confidence_score": 0.95},
        {"product_name": "Milk", "price": 1001, "confidence_score": 0.95},
    ],
)
def test_convert_summary_to_product_sets_price_none_when_unreliable(summary_payload):
    product = _convert_summary(summary_payload)
    assert product is not None
    assert product["price"] is None


def test_convert_summary_to_product_keeps_price_when_confident_and_valid():
    product = _convert_summary({"product_name": "Milk", "price": 4.99, "confidence_score": 0.9})
    assert product is not None
    assert product["price"] == 4.99
