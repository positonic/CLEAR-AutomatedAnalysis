"""Publisher — turn one CLEAR run into a stored Situation Analysis for a country.

Orchestrates the I/O side of a run: ensure the Country location exists, archive
each source PDF (content-hash key), stamp the returned ``s3Key`` onto the
matching bundle source, then upsert the whole bundle as one
``clear_situation_analysis`` record. The standalone dashboard `.js` files are
still written by generate_dashboard_data — this only adds the cached record.

The PDF loader is injected so the orchestration unit-tests with a fake client +
fake loader, no network or filesystem.
"""

from __future__ import annotations

import os
from hashlib import sha256
from typing import Any, Callable, Dict, List, Optional, Sequence

from src.analysis.clear_api_client import ClearApiClient

# Per-country level-0 bounding boxes [minLng, minLat, maxLng, maxLat], mirroring
# the frontend per-country config. ensureCountryLocation turns these into the
# Country's MULTIPOLYGON geometry. Add a country here to bring it into scope.
COUNTRY_BBOX: Dict[str, List[float]] = {
    "Sudan": [21.8, 8.5, 38.6, 22.0],
    "Lebanon": [35.1, 33.05, 36.65, 34.69],
}

# A loader resolves a bundle source entry to its PDF bytes (or None if absent).
SourcePdfLoader = Callable[[Dict[str, Any]], Optional[bytes]]


class PublishError(RuntimeError):
    pass


def _pdf_filename(source: Dict[str, Any]) -> str:
    """A stable, human-ish filename for the upload (the stored key is the
    content hash regardless, so this is cosmetic)."""
    link = source.get("link")
    if link:
        base = os.path.basename(str(link).split("?")[0])
        if base.lower().endswith(".pdf"):
            return base
    return "source.pdf"


def pdf_loader_from_dir(pdf_dir: str) -> SourcePdfLoader:
    """Build a loader that reads a source's PDF from ``pdf_dir`` by the URL's
    basename, returning None when the file is missing. Best-effort: the leads
    connector downloads PDFs into ``data/{project}/pdf_files/``.
    """

    def _load(source: Dict[str, Any]) -> Optional[bytes]:
        link = source.get("link")
        if not link:
            return None
        candidate = os.path.join(pdf_dir, os.path.basename(str(link).split("?")[0]))
        if not candidate.lower().endswith(".pdf"):
            candidate += ".pdf"
        if os.path.isfile(candidate):
            with open(candidate, "rb") as fh:
                return fh.read()
        return None

    return _load


def resolve_bbox(country: str, country_bbox: Dict[str, Sequence[float]] = COUNTRY_BBOX) -> List[float]:
    bbox = country_bbox.get(country)
    if bbox is None:
        raise PublishError(
            f"no bounding box configured for country {country!r}; "
            f"add it to COUNTRY_BBOX (mirroring the frontend per-country config)"
        )
    return list(bbox)


def publish_situation_analysis(
    client: ClearApiClient,
    country: str,
    bundle: Dict[str, Any],
    source_pdf_loader: Optional[SourcePdfLoader] = None,
    bbox: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    """Publish one country's bundle end-to-end.

    1. ensure the Country location (find-or-create with bbox geometry),
    2. archive each source PDF the loader can resolve, stamping ``s3Key``,
    3. upsert the bundle as the country's current ``clear_situation_analysis``.

    Returns ``{ locationId, record, archived }``.
    """
    resolved_bbox = list(bbox) if bbox is not None else resolve_bbox(country)
    location_id = client.ensure_country_location(country, resolved_bbox)

    archived = 0
    if source_pdf_loader is not None:
        for source in bundle.get("sources", []):
            pdf_bytes = source_pdf_loader(source)
            if not pdf_bytes:
                continue
            source["s3Key"] = client.upload_source_pdf(
                pdf_bytes, filename=_pdf_filename(source)
            )
            archived += 1

    record = client.upsert_situation_analysis(location_id, bundle)
    return {"locationId": location_id, "record": record, "archived": archived}


def content_hash_key(pdf_bytes: bytes) -> str:
    """The S3 key clear-api will assign — useful for dry-run logging."""
    return f"sources/{sha256(pdf_bytes).hexdigest()}.pdf"
