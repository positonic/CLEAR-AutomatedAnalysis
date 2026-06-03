"""clear-api client — the pipeline's thin I/O boundary to clear-api.

Three operations, all authenticated with the least-privilege pipeline API key
(``Bearer sk_live_…``):

  - ``ensure_country_location(name, bbox) -> location_id`` (GraphQL mutation),
  - ``upload_source_pdf(pdf_bytes) -> s3_key`` (REST multipart upload),
  - ``upsert_situation_analysis(location_id, data)`` (GraphQL mutation).

Network calls go through an injected ``requests.Session`` so the surface is
unit-testable with a fake transport.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import requests

SITUATION_ANALYSIS_TYPE = "clear_situation_analysis"

_ENSURE_COUNTRY = (
    "mutation($name:String!,$bbox:[Float!]!){"
    "ensureCountryLocation(name:$name,bbox:$bbox){id name}}"
)
_UPSERT_METADATA = (
    "mutation($input:UpsertLocationMetadataInput!){"
    "upsertLocationMetadata(input:$input){id type validFrom validTo}}"
)


class ClearApiError(RuntimeError):
    """Raised when clear-api returns a GraphQL error or a non-2xx response."""


class ClearApiClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        session: Optional[requests.Session] = None,
        timeout: int = 60,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._graphql_url = f"{self._base}/graphql"
        self._upload_url = f"{self._base}/api/upload"
        self._api_key = api_key
        self._timeout = timeout
        self._session = session or requests.Session()

    @property
    def _auth_header(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _graphql(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._session.post(
            self._graphql_url,
            json={"query": query, "variables": variables},
            headers={**self._auth_header, "Content-Type": "application/json"},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("errors"):
            raise ClearApiError(str(body["errors"]))
        return body["data"]

    def ensure_country_location(self, name: str, bbox: Sequence[float]) -> str:
        """Find-or-create the level-0 Country, returning its id."""
        data = self._graphql(_ENSURE_COUNTRY, {"name": name, "bbox": list(bbox)})
        return data["ensureCountryLocation"]["id"]

    def upload_source_pdf(
        self, pdf_bytes: bytes, filename: str = "source.pdf"
    ) -> str:
        """Archive a source PDF, returning its ``sources/{sha256}.pdf`` key."""
        resp = self._session.post(
            self._upload_url,
            files={"files": (filename, pdf_bytes, "application/pdf")},
            headers=self._auth_header,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        keys: List[str] = resp.json().get("keys", [])
        if not keys:
            raise ClearApiError("upload returned no keys")
        return keys[0]

    def upsert_situation_analysis(
        self, location_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upsert the country's ``clear_situation_analysis`` bundle record."""
        result = self._graphql(
            _UPSERT_METADATA,
            {
                "input": {
                    "locationId": location_id,
                    "type": SITUATION_ANALYSIS_TYPE,
                    "data": data,
                }
            },
        )
        return result["upsertLocationMetadata"]
