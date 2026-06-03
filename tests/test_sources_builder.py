"""Unit tests for the pure sources builder."""

import pandas as pd

from src.analysis.sources_builder import (
    TYPE_GOVERNMENT,
    TYPE_NGO,
    TYPE_OTHER,
    TYPE_UN,
    build_sources,
    categorize_source_type,
)

# A hermetic resolver standing in for the RW connector's get_source_types →
# categorize pipeline. Unknown orgs resolve to "Other" (the connector behaviour).
_LABELS = {
    "UNHCR": "International Organization",
    "Save the Children": "Non-governmental Organization",
    "Government of Sudan": "Government",
}


def resolver(org: str) -> str:
    return categorize_source_type(_LABELS.get(org))


def test_categorize_source_type_mapping():
    assert categorize_source_type("International Organization") == TYPE_UN
    assert categorize_source_type("Non-governmental Organization") == TYPE_NGO
    assert categorize_source_type("Government") == TYPE_GOVERNMENT
    assert categorize_source_type("Academic Institution") == TYPE_OTHER
    assert categorize_source_type(None) == TYPE_OTHER


def test_basic_join_enriches_entry():
    leads = pd.DataFrame(
        [
            {
                "Document Source": ["UNHCR"],
                "Document Title": "Sudan Flash Update",
                "Document URL": "https://reliefweb.int/1.pdf",
                "Document Publishing Date": "2026-03-20",
            }
        ]
    )
    res = build_sources(["UNHCR"], leads, type_resolver=resolver)
    assert len(res) == 1
    entry = res[0]
    assert entry == {
        "title": "Sudan Flash Update",
        "org": "UNHCR",
        "type": TYPE_UN,
        "link": "https://reliefweb.int/1.pdf",
        "publishedDate": "2026-03-20",
        "s3Key": None,
    }


def test_unknown_org_maps_to_other():
    leads = pd.DataFrame(
        [
            {
                "Document Source": ["MysteryOrg"],
                "Document Title": "Report",
                "Document URL": "https://x/2.pdf",
                "Document Publishing Date": "2026-02-01",
            }
        ]
    )
    res = build_sources(["MysteryOrg"], leads, type_resolver=resolver)
    assert res[0]["type"] == TYPE_OTHER


def test_missing_url_kept_and_deduped_by_org_title():
    leads = pd.DataFrame(
        [
            {
                "Document Source": ["Save the Children"],
                "Document Title": "Child Protection Brief",
                "Document URL": None,
                "Document Publishing Date": "2026-01-15",
            },
            # Exact duplicate (no URL) — must dedupe to one entry.
            {
                "Document Source": ["Save the Children"],
                "Document Title": "Child Protection Brief",
                "Document URL": None,
                "Document Publishing Date": "2026-01-15",
            },
        ]
    )
    res = build_sources(["Save the Children"], leads, type_resolver=resolver)
    assert len(res) == 1
    assert res[0]["link"] is None
    assert res[0]["type"] == TYPE_NGO


def test_multiple_orgs_per_document_dedupes_by_link():
    leads = pd.DataFrame(
        [
            {
                "Document Source": ["OrgA", "OrgB"],
                "Document Title": "Joint Assessment",
                "Document URL": "https://x/joint.pdf",
                "Document Publishing Date": "2026-04-01",
            }
        ]
    )
    res = build_sources(
        ["OrgA", "OrgB"], leads, type_resolver=lambda o: TYPE_NGO if o == "OrgB" else TYPE_UN
    )
    # Same document cited under two orgs → one entry (deduped by link), attributed
    # to the first cited org that matched.
    assert len(res) == 1
    assert res[0]["link"] == "https://x/joint.pdf"
    assert res[0]["org"] == "OrgA"


def test_stringified_list_document_source():
    leads = pd.DataFrame(
        [
            {
                "Document Source": "['UNHCR']",
                "Document Title": "t",
                "Document URL": "https://x/3.pdf",
                "Document Publishing Date": "d",
            }
        ]
    )
    res = build_sources(["UNHCR"], leads, type_resolver=resolver)
    assert len(res) == 1 and res[0]["org"] == "UNHCR"


def test_empty_leads_returns_empty():
    assert build_sources(["UNHCR"], pd.DataFrame()) == []


def test_uncited_org_is_ignored():
    leads = pd.DataFrame(
        [
            {
                "Document Source": ["UNHCR"],
                "Document Title": "t",
                "Document URL": "u",
                "Document Publishing Date": "d",
            }
        ]
    )
    # We only cite "OCHA", which has no leads row → no entries.
    assert build_sources(["OCHA"], leads, type_resolver=resolver) == []
