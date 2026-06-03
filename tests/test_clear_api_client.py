"""Unit tests for the clear-api client with a fake requests transport."""

import pytest

from src.analysis.clear_api_client import ClearApiError, ClearApiClient


class FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self._responses.pop(0)


def client(responses):
    return ClearApiClient("http://api", "sk_live_test", session=FakeSession(responses))


def test_ensure_country_location_builds_mutation_and_parses_id():
    c = client([FakeResp({"data": {"ensureCountryLocation": {"id": "loc1", "name": "Sudan"}}})])
    loc = c.ensure_country_location("Sudan", [21.8, 8.5, 38.6, 22.0])
    assert loc == "loc1"

    url, kwargs = c._session.calls[0]  # type: ignore[attr-defined]
    assert url == "http://api/graphql"
    assert kwargs["json"]["variables"] == {"name": "Sudan", "bbox": [21.8, 8.5, 38.6, 22.0]}
    assert kwargs["headers"]["Authorization"] == "Bearer sk_live_test"


def test_upload_source_pdf_posts_multipart_and_returns_key():
    c = client([FakeResp({"keys": ["sources/abc123.pdf"]})])
    key = c.upload_source_pdf(b"%PDF-1.4", "doc.pdf")
    assert key == "sources/abc123.pdf"

    url, kwargs = c._session.calls[0]  # type: ignore[attr-defined]
    assert url == "http://api/api/upload"
    assert "files" in kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer sk_live_test"


def test_upload_with_no_keys_raises():
    c = client([FakeResp({"keys": []})])
    with pytest.raises(ClearApiError):
        c.upload_source_pdf(b"%PDF")


def test_upsert_situation_analysis_builds_input():
    c = client(
        [
            FakeResp(
                {
                    "data": {
                        "upsertLocationMetadata": {
                            "id": "m1",
                            "type": "clear_situation_analysis",
                            "validFrom": "t",
                            "validTo": None,
                        }
                    }
                }
            )
        ]
    )
    rec = c.upsert_situation_analysis("loc1", {"summary": None, "final_numbers": {}})
    assert rec["id"] == "m1"

    url, kwargs = c._session.calls[0]  # type: ignore[attr-defined]
    inp = kwargs["json"]["variables"]["input"]
    assert inp["locationId"] == "loc1"
    assert inp["type"] == "clear_situation_analysis"
    assert inp["data"] == {"summary": None, "final_numbers": {}}


def test_graphql_errors_raise_clear_api_error():
    c = client([FakeResp({"errors": [{"message": "Insufficient permissions"}]})])
    with pytest.raises(ClearApiError):
        c.ensure_country_location("X", [1, 2, 3, 4])
