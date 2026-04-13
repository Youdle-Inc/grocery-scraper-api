import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scraper.location_service import LocationService


def test_heb_is_excluded_for_chicago_zip():
    service = LocationService(google_api_key="")

    assert service.is_store_available_in_zipcode("heb", "60616") is False
    assert asyncio.run(service.verify_store_in_zipcode("heb", "60616")) is False
    assert asyncio.run(service.resolve_store_ids_by_location(["heb"], "60616")) == []


def test_non_local_store_is_excluded_for_chicago_zip():
    service = LocationService(google_api_key="")

    assert service.is_store_available_in_zipcode("wegmans", "60616") is False
    assert asyncio.run(service.verify_store_in_zipcode("wegmans", "60616")) is False
    assert asyncio.run(service.resolve_store_ids_by_location(["wegmans"], "60616")) == []


def test_kroger_is_excluded_for_rochester_zip_without_places_verification():
    service = LocationService(google_api_key="")

    assert service.is_store_available_in_zipcode("kroger", "14610") is False
    assert asyncio.run(service.verify_store_in_zipcode("kroger", "14610")) is False
    assert asyncio.run(service.resolve_store_ids_by_location(["kroger"], "14610")) == []


def test_marianos_is_included_for_chicago_zip():
    service = LocationService(google_api_key="")

    assert service.is_store_available_in_zipcode("marianos", "60616") is True
    assert asyncio.run(service.verify_store_in_zipcode("marianos", "60616")) is True
    assert asyncio.run(service.resolve_store_ids_by_location(["marianos"], "60616")) == ["marianos"]


def test_unknown_store_can_pass_with_places_verification(monkeypatch):
    service = LocationService(google_api_key="fake-key")

    async def fake_search_stores_via_places_api(store_id: str, zipcode: str, radius_meters: int = 16093):
        return [
            {
                "name": "H-E-B",
                "address": "123 Example St",
                "place_id": "place-123",
                "location": {"lat": 29.76, "lng": -95.37},
            }
        ]

    monkeypatch.setattr(service, "search_stores_via_places_api", fake_search_stores_via_places_api)

    assert asyncio.run(service.verify_store_in_zipcode("heb", "60616")) is True
    assert asyncio.run(service.resolve_store_ids_by_location(["heb"], "60616")) == ["heb"]
