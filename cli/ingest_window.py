"""Rolling ReliefWeb ingest window + date-stamped run scope.

Pure, side-effect-free helpers (stdlib only) that turn a *run date* into:

  - the ReliefWeb advanced-search URL carrying a rolling ``DO<start>-<end>``
    date window (replacing the previously hardcoded range), and
  - a date-stamped ``project_name`` so each day's run writes to a fresh folder.

The pipeline is idempotent-by-file: a step is skipped when its output already
exists. Date-stamping the project folder keeps that behaviour *within* a run
(reruns the same day are no-ops) while letting the next day's run re-ingest
fresh data instead of skipping everything.

Kept dependency-free so they unit-test without the pipeline's heavy ML stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

DEFAULT_WINDOW_DAYS = 7
# ReliefWeb country code for Sudan. The advanced-search query is
# ``(C<country>)_(DO<start>-<end>)``; ``&page={}`` is the placeholder
# get_reliefweb_leads fills per page.
DEFAULT_COUNTRY_CODE = "C220"
_RW_TEMPLATE = (
    "https://reliefweb.int/updates?advanced-search="
    "%28{country}%29_%28DO{start}-{end}%29&page={{}}"
)
_DATE_FMT = "%Y%m%d"


@dataclass(frozen=True)
class IngestWindow:
    """An inclusive ``[start, end]`` ingest window."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"window end {self.end} precedes start {self.start}")

    @property
    def days(self) -> int:
        """Number of days covered, inclusive of both endpoints."""
        return (self.end - self.start).days + 1

    def rw_param(self) -> str:
        """The ``YYYYMMDD-YYYYMMDD`` fragment used in the RW ``DO`` filter."""
        return f"{self.start:{_DATE_FMT}}-{self.end:{_DATE_FMT}}"


def rolling_window(run_date: date, n_days: int = DEFAULT_WINDOW_DAYS) -> IngestWindow:
    """An ``n_days``-day window ending (inclusive) on ``run_date``."""
    if n_days < 1:
        raise ValueError(f"n_days must be >= 1, got {n_days}")
    return IngestWindow(start=run_date - timedelta(days=n_days - 1), end=run_date)


def parse_window(spec: str) -> IngestWindow:
    """Parse an explicit ``YYYYMMDD-YYYYMMDD`` window (for pinned reruns)."""
    parts = spec.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"invalid window {spec!r}; expected YYYYMMDD-YYYYMMDD")
    try:
        start = datetime.strptime(parts[0], _DATE_FMT).date()
        end = datetime.strptime(parts[1], _DATE_FMT).date()
    except ValueError as exc:
        raise ValueError(
            f"invalid window {spec!r}; expected YYYYMMDD-YYYYMMDD"
        ) from exc
    return IngestWindow(start=start, end=end)


def parse_run_date(spec: str) -> date:
    """Parse a ``YYYYMMDD`` run date (for pinned reruns)."""
    try:
        return datetime.strptime(spec.strip(), _DATE_FMT).date()
    except ValueError as exc:
        raise ValueError(f"invalid run date {spec!r}; expected YYYYMMDD") from exc


def build_rw_url(window: IngestWindow, country_code: str = DEFAULT_COUNTRY_CODE) -> str:
    """Build the ReliefWeb advanced-search URL for ``window`` and country."""
    return _RW_TEMPLATE.format(
        country=country_code,
        start=f"{window.start:{_DATE_FMT}}",
        end=f"{window.end:{_DATE_FMT}}",
    )


def date_stamped_project_name(base: str, run_date: date) -> str:
    """``{base}_{YYYYMMDD}`` — the per-run output folder name."""
    return f"{base}_{run_date:{_DATE_FMT}}"
