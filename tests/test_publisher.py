"""Unit tests for the publisher orchestration with a fake clear-api client."""

import pytest

from src.analysis.publisher import (
    PublishError,
    content_hash_key,
    publish_situation_analysis,
    resolve_bbox,
)


class FakeClient:
    def __init__(self):
        self.ensured = None
        self.uploads = []
        self.upserted = None

    def ensure_country_location(self, name, bbox):
        self.ensured = (name, list(bbox))
        return f"loc-{name}"

    def upload_source_pdf(self, pdf_bytes, filename="source.pdf"):
        self.uploads.append((pdf_bytes, filename))
        return f"sources/{len(self.uploads)}.pdf"

    def upsert_situation_analysis(self, location_id, data):
        self.upserted = (location_id, data)
        return {"id": "rec1", "validTo": None}


def test_resolve_bbox_known_and_unknown():
    assert resolve_bbox("Sudan") == [21.8, 8.5, 38.6, 22.0]
    with pytest.raises(PublishError):
        resolve_bbox("Atlantis")


def test_publish_orders_ensure_then_upload_then_upsert_and_sets_s3key():
    bundle = {
        "sources": [
            {"org": "A", "link": "http://x/1.pdf", "s3Key": None},
            {"org": "B", "link": None, "s3Key": None},
        ],
        "summary": None,
    }
    loader = lambda src: b"%PDF" if src["link"] else None  # noqa: E731
    client = FakeClient()

    result = publish_situation_analysis(client, "Sudan", bundle, source_pdf_loader=loader)

    # Country ensured with the configured bbox.
    assert client.ensured == ("Sudan", [21.8, 8.5, 38.6, 22.0])
    # Only the source with a resolvable PDF was archived; its s3Key stamped.
    assert result["archived"] == 1
    assert bundle["sources"][0]["s3Key"] == "sources/1.pdf"
    assert bundle["sources"][1]["s3Key"] is None
    # Upsert received the bundle (with the stamped s3Key) under the right location.
    assert client.upserted[0] == "loc-Sudan"
    assert client.upserted[1]["sources"][0]["s3Key"] == "sources/1.pdf"


def test_publish_without_loader_still_ensures_and_upserts():
    client = FakeClient()
    result = publish_situation_analysis(
        client, "Lebanon", {"sources": [{"org": "A", "link": "x"}]}
    )
    assert result["archived"] == 0
    assert client.ensured[0] == "Lebanon"
    assert client.upserted is not None


def test_publish_unknown_country_raises():
    with pytest.raises(PublishError):
        publish_situation_analysis(FakeClient(), "Atlantis", {"sources": []})


def test_content_hash_key_is_deterministic():
    k1 = content_hash_key(b"%PDF same")
    k2 = content_hash_key(b"%PDF same")
    assert k1 == k2
    assert k1.startswith("sources/") and k1.endswith(".pdf")
    assert content_hash_key(b"different") != k1
