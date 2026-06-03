"""Sources builder — pure mapping from cited source names + the leads table to
the enriched ``sources[]`` list carried in the Situation Analysis bundle.

Each entry is ``{ title, org, type, link, publishedDate, s3Key }``. ``s3Key`` is
left ``None`` here; the publisher fills it after archiving the document's PDF
(content-hash key from clear-api's upload route). The org→type categorisation is
injectable so the join logic unit-tests without the data_connectors stack.
"""

from __future__ import annotations

from ast import literal_eval
from typing import Any, Callable, Dict, List, Optional, Sequence

import pandas as pd

# Bundle source-type categories.
TYPE_UN = "UN"
TYPE_NGO = "NGO"
TYPE_GOVERNMENT = "Government"
TYPE_OTHER = "Other"

# ReliefWeb connector source-type labels → bundle categories. Unknown labels
# fall back to "Other".
_LABEL_TO_CATEGORY = {
    "international organization": TYPE_UN,
    "united nations": TYPE_UN,
    "non-governmental organization": TYPE_NGO,
    "government": TYPE_GOVERNMENT,
}


def categorize_source_type(label: Optional[str]) -> str:
    """Map a ReliefWeb connector source-type label to a bundle category."""
    if not label:
        return TYPE_OTHER
    return _LABEL_TO_CATEGORY.get(str(label).strip().lower(), TYPE_OTHER)


def default_type_resolver(org: str) -> str:
    """Resolve an org name to a bundle type category via the RW connector's
    bundled source-type metadata. Imported lazily so the pure builder stays
    dependency-free; unknown/unmapped orgs become "Other"."""
    try:
        from data_connectors.reliefweb.scraper import get_source_types

        labels = get_source_types([org])
    except Exception:
        return TYPE_OTHER
    return categorize_source_type(labels[0] if labels else None)


def _orgs_of(value: Any) -> List[str]:
    """Normalise a leads `Document Source` cell to a list of org names.

    The column may hold a real list, a stringified list (``"['A', 'B']"``), or a
    plain scalar. Handles the multiple-orgs-per-document case.
    """
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = literal_eval(text)
            if isinstance(parsed, (list, tuple)):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except (ValueError, SyntaxError):
            pass
    return [text] if text else []


def _clean(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def build_sources(
    cited_source_names: Sequence[str],
    leads_df: pd.DataFrame,
    type_resolver: Callable[[str], str] = default_type_resolver,
) -> List[Dict[str, Any]]:
    """Build the enriched ``sources[]`` list.

    For each cited org name, find the leads documents attributed to it and emit
    one entry per document, joining ``Document Title`` / ``Document URL`` /
    ``Document Publishing Date``. Documents are de-duplicated by link (falling
    back to ``(org, title)`` when the URL is missing), so a document cited under
    several orgs appears once.

    Args:
        cited_source_names: org names cited in the analysis (e.g. from
            generate_top_5_sources).
        leads_df: the leads table with columns ``Document Source``,
            ``Document Title``, ``Document URL``, ``Document Publishing Date``.
        type_resolver: org name → bundle type category. Defaults to the RW
            connector's metadata; inject a stub in tests.

    Returns:
        A list of ``{ title, org, type, link, publishedDate, s3Key }`` dicts
        (``s3Key`` is ``None`` until the publisher archives the PDF).
    """
    if leads_df is None or leads_df.empty:
        return []

    sources: List[Dict[str, Any]] = []
    seen: set = set()
    # Resolve each cited org's type once.
    type_cache: Dict[str, str] = {}

    for raw_name in cited_source_names:
        org = str(raw_name).strip()
        if not org:
            continue
        if org not in type_cache:
            type_cache[org] = type_resolver(org)
        category = type_cache[org]

        for _, row in leads_df.iterrows():
            if org not in _orgs_of(row.get("Document Source")):
                continue
            title = _clean(row.get("Document Title"))
            link = _clean(row.get("Document URL"))
            published = _clean(row.get("Document Publishing Date"))

            dedup_key = link if link else (org, title)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            sources.append(
                {
                    "title": title,
                    "org": org,
                    "type": category,
                    "link": link,
                    "publishedDate": published,
                    "s3Key": None,
                }
            )

    return sources
