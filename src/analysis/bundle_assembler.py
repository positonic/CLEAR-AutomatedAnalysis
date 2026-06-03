"""Bundle assembler — pure mapping from analysis outputs to the canonical
Situation Analysis bundle stored behind clear-api.

The bundle is a single JSON record (one current per country) carrying the ~13
dashboard structures plus the enriched ``sources`` list, a reserved ``summary``
slot (filled later by AutoSitRep), and provenance. Kept pure (no I/O, no
pandas) so it is trivially unit-testable and survives refactors of the
generators that feed it.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

# The 13 dashboard structures, in the order documented in the storage contract.
# Each is produced by a `generate_*` function in generate_ui.py.
BUNDLE_STRUCTURE_KEYS: tuple[str, ...] = (
    "final_numbers",
    "displacement",
    "shown_risks",
    "humanitarian_access",
    "key_sector_numbers",
    "current_hazards_and_threats",
    "precrisis_vulnerabilities",
    "displacement_risks",
    "top_sectoral_needs",
    "top_priority_interventions",
    "top_5_sources",
    "output_context_risks",
    "information_coverage",
)


def assemble_bundle(
    structures: Dict[str, Any],
    sources: Sequence[Dict[str, Any]],
    project_name: str,
    generated_at: str,
    summary: Optional[Any] = None,
) -> Dict[str, Any]:
    """Assemble the canonical bundle dict.

    Args:
        structures: mapping of the 13 structure keys to their computed values.
            Missing keys default to ``None`` and empty sub-structures (``{}`` /
            ``[]``) are passed through untouched.
        sources: enriched ``sources`` entries (see sources_builder).
        project_name: the date-stamped run project (provenance).
        generated_at: ISO-8601 timestamp of when the bundle was produced.
        summary: reserved for AutoSitRep; defaults to ``None``.

    Returns:
        The bundle dict with all structure keys, ``sources``, ``summary``, and
        ``generatedAt`` / ``projectName`` provenance.
    """
    bundle: Dict[str, Any] = {
        key: structures.get(key) for key in BUNDLE_STRUCTURE_KEYS
    }
    bundle["sources"] = list(sources)
    bundle["summary"] = summary  # reserved slot — AutoSitRep fills it later
    bundle["generatedAt"] = generated_at
    bundle["projectName"] = project_name
    return bundle


def bundle_keys() -> List[str]:
    """All top-level keys the assembled bundle is expected to carry."""
    return [
        *BUNDLE_STRUCTURE_KEYS,
        "sources",
        "summary",
        "generatedAt",
        "projectName",
    ]
