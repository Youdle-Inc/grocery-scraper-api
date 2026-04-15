import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scraper.exa_structured_client import ExaStructuredClient


@pytest.mark.parametrize(
    "url",
    [
        "https://www.wegmans.com/shop/product/59715-Hi-Pro-Ultra-Filtered-Fat-Free-Milk",
        "https://shop.wegmans.com/product/41663/wegmans-milk-lactose-free-fat-free",
    ],
)
def test_is_product_page_accepts_safe_wegmans_product_urls(url):
    client = ExaStructuredClient(api_key=None)
    assert client._is_product_page(url, "Wegmans Milk")


@pytest.mark.parametrize(
    "url",
    [
        "https://order.wegmans.com/store/wegmans/products/18207586-raw-sugar-shampoo-the-moisture-smoothie-18-fl-oz",
        "https://www.wegmans.com/stores/east-ave-ny",
        "https://www.wegmans.com/shop/categories/2952075",
        "https://www.wegmans.com/service/faq/product-information",
    ],
)
def test_is_product_page_rejects_non_catalog_wegmans_urls(url):
    client = ExaStructuredClient(api_key=None)
    assert not client._is_product_page(url, "Wegmans")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.notwegmans.com/shop/product/59715-fake",
        "https://wegmans.com.evil.test/shop/product/59715-fake",
    ],
)
def test_sanitize_wegmans_product_url_does_not_treat_lookalike_hosts_as_wegmans(url):
    client = ExaStructuredClient(api_key=None)
    assert client._sanitize_wegmans_product_url(url) == url


@pytest.mark.parametrize(
    ("url", "expected_store_id"),
    [
        ("https://www.wegmans.com/shop/product/59715-Hi-Pro-Ultra-Filtered-Fat-Free-Milk", "wegmans"),
        ("https://shop.wegmans.com/product/41663/wegmans-milk-lactose-free-fat-free", "wegmans"),
        ("https://wegmans.com.evil.test/shop/product/123", None),
        ("https://www.notwegmans.com/shop/product/123", None),
    ],
)
def test_detect_store_from_url_uses_strict_hostname_matching(url, expected_store_id):
    client = ExaStructuredClient(api_key=None)
    assert client._detect_store_from_url(url) == expected_store_id
