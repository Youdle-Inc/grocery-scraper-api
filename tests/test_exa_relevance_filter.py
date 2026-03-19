import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scraper.exa_structured_client import ExaStructuredClient


class FakeResult:
    def __init__(self, url: str, title: str):
        self.url = url
        self.title = title
        self.summary = None
        self.text = ""


def test_single_token_near_match_is_filtered(monkeypatch):
    client = ExaStructuredClient(api_key=None)

    async def fake_extract_product_data(result, store_name, zipcode, extract_images_async=False):
        return {
            "name": "Silk",
            "product_url": result.url,
            "store_name": store_name,
        }

    monkeypatch.setattr(client, "_extract_product_data", fake_extract_product_data)

    result = FakeResult(
        url="https://example.com/product/123",
        title="Silk"
    )

    out = __import__("asyncio").run(
        client._process_single_result(
            result=result,
            store_name="Target",
            zipcode="38125",
            query="milk",
            idx=0,
        )
    )

    assert out is None


def test_relevant_result_is_kept(monkeypatch):
    client = ExaStructuredClient(api_key=None)

    async def fake_extract_product_data(result, store_name, zipcode, extract_images_async=False):
        return {
            "name": "Organic Whole Milk",
            "product_url": result.url,
            "store_name": store_name,
        }

    monkeypatch.setattr(client, "_extract_product_data", fake_extract_product_data)

    result = FakeResult(
        url="https://example.com/product/456",
        title="Organic Whole Milk"
    )

    out = __import__("asyncio").run(
        client._process_single_result(
            result=result,
            store_name="Target",
            zipcode="38125",
            query="milk",
            idx=0,
        )
    )

    assert out is not None
    assert out["name"] == "Organic Whole Milk"
