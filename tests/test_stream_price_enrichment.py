import asyncio

from scraper.stream_price_enrichment import enrich_stream_products_with_prices


class FakeWebSearchService:
    def __init__(self, price=4.99, should_raise=False):
        self.price = price
        self.should_raise = should_raise
        self.calls = []

    async def batch_verify_prices(self, products):
        self.calls.append(products)
        if self.should_raise:
            raise RuntimeError("verification failed")
        for product in products:
            product["price"] = self.price
        return products


def test_existing_numeric_price_is_preserved_without_verification():
    service = FakeWebSearchService()
    products = [{"name": "Milk", "price": 3.99, "product_url": "https://example.com/milk"}]

    result = asyncio.run(enrich_stream_products_with_prices(products, service))

    assert result[0]["price"] == 3.99
    assert service.calls == []


def test_existing_string_price_is_normalized_without_verification():
    service = FakeWebSearchService()
    products = [{"name": "Milk", "price": "$5.49", "product_url": "https://example.com/milk"}]

    result = asyncio.run(enrich_stream_products_with_prices(products, service))

    assert result[0]["price"] == 5.49
    assert service.calls == []


def test_missing_price_is_verified_when_product_url_exists():
    service = FakeWebSearchService(price=6.25)
    products = [{"name": "Grapes", "price": None, "product_url": "https://example.com/grapes"}]

    result = asyncio.run(enrich_stream_products_with_prices(products, service))

    assert result[0]["price"] == 6.25
    assert len(service.calls) == 1
    assert service.calls[0][0]["product_url"] == "https://example.com/grapes"


def test_missing_price_without_product_url_is_left_unavailable():
    service = FakeWebSearchService(price=6.25)
    products = [{"name": "Grapes", "price": None, "product_url": None}]

    result = asyncio.run(enrich_stream_products_with_prices(products, service))

    assert result[0].get("price") is None
    assert service.calls == []


def test_verification_failure_does_not_drop_product():
    service = FakeWebSearchService(should_raise=True)
    products = [{"name": "Grapes", "price": None, "product_url": "https://example.com/grapes"}]

    result = asyncio.run(enrich_stream_products_with_prices(products, service))

    assert result == products
    assert result[0].get("price") is None
