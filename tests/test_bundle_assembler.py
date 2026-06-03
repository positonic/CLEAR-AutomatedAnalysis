"""Unit tests for the pure bundle assembler."""

from src.analysis.bundle_assembler import (
    BUNDLE_STRUCTURE_KEYS,
    assemble_bundle,
    bundle_keys,
)


def test_bundle_has_all_keys_summary_null_and_provenance():
    structures = {k: {"value": k} for k in BUNDLE_STRUCTURE_KEYS}
    bundle = assemble_bundle(
        structures,
        sources=[{"org": "UNHCR", "type": "UN"}],
        project_name="Sudan2026_20260603",
        generated_at="2026-06-03T00:00:00+00:00",
    )

    for key in bundle_keys():
        assert key in bundle

    assert bundle["summary"] is None
    assert bundle["projectName"] == "Sudan2026_20260603"
    assert bundle["generatedAt"] == "2026-06-03T00:00:00+00:00"
    assert bundle["sources"] == [{"org": "UNHCR", "type": "UN"}]
    for key in BUNDLE_STRUCTURE_KEYS:
        assert bundle[key] == {"value": key}


def test_tolerates_empty_and_missing_substructures():
    structures = {"final_numbers": {}, "shown_risks": []}  # the rest are missing
    bundle = assemble_bundle(structures, sources=[], project_name="P", generated_at="T")

    assert bundle["final_numbers"] == {}
    assert bundle["shown_risks"] == []
    # Missing structures are present as None (key always exists).
    assert bundle["displacement"] is None
    assert set(bundle_keys()).issubset(bundle.keys())


def test_summary_slot_can_be_overridden():
    bundle = assemble_bundle({}, [], "P", "T", summary={"sitrep": "text"})
    assert bundle["summary"] == {"sitrep": "text"}


def test_sources_are_copied_not_aliased():
    src = [{"org": "A"}]
    bundle = assemble_bundle({}, src, "P", "T")
    src.append({"org": "B"})
    assert bundle["sources"] == [{"org": "A"}]
