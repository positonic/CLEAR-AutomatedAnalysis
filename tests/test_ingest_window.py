"""Direct unit tests for the rolling-window / run-scope helpers.

These are the pipeline repo's first tests. They cover the pure mapping
``run date → (RW URL, project_name)`` and the pinned-replay parsing, with no
dependency on the heavy ML stack.
"""

from datetime import date

import pytest

from cli.ingest_window import (
    DEFAULT_COUNTRY_CODE,
    IngestWindow,
    build_rw_url,
    date_stamped_project_name,
    parse_run_date,
    parse_window,
    rolling_window,
)

# The original hardcoded behaviour the rolling window must reproduce when the
# run date is 2026-03-21 with the default 7-day window.
LEGACY_URL = (
    "https://reliefweb.int/updates?advanced-search="
    "%28C220%29_%28DO20260315-20260321%29&page={}"
)


def test_rolling_window_is_n_days_ending_on_run_date():
    win = rolling_window(date(2026, 3, 21), 7)
    assert win.start == date(2026, 3, 15)
    assert win.end == date(2026, 3, 21)
    assert win.days == 7
    assert win.rw_param() == "20260315-20260321"


def test_rolling_window_single_day():
    win = rolling_window(date(2026, 6, 3), 1)
    assert win.start == win.end == date(2026, 6, 3)
    assert win.days == 1


def test_rolling_window_rejects_non_positive_n():
    with pytest.raises(ValueError):
        rolling_window(date(2026, 6, 3), 0)


def test_build_rw_url_reproduces_legacy_url():
    win = rolling_window(date(2026, 3, 21), 7)
    assert build_rw_url(win) == LEGACY_URL
    # The page placeholder must survive for get_reliefweb_leads to fill.
    assert "&page={}" in build_rw_url(win)


def test_build_rw_url_honours_country_code():
    win = rolling_window(date(2026, 3, 21), 7)
    assert "%28C115%29" in build_rw_url(win, country_code="C115")
    assert DEFAULT_COUNTRY_CODE == "C220"


def test_date_stamped_project_name():
    assert (
        date_stamped_project_name("Sudan2026", date(2026, 3, 21))
        == "Sudan2026_20260321"
    )


def test_consecutive_run_dates_yield_distinct_scope_and_window():
    """Acceptance: date X vs X+1 → distinct folder + different reports."""
    day_x = date(2026, 6, 3)
    day_x1 = date(2026, 6, 4)
    base, n = "Sudan2026", 7

    name_x = date_stamped_project_name(base, day_x)
    name_x1 = date_stamped_project_name(base, day_x1)
    assert name_x != name_x1  # distinct date-stamped output dirs

    url_x = build_rw_url(rolling_window(day_x, n))
    url_x1 = build_rw_url(rolling_window(day_x1, n))
    assert url_x != url_x1  # window shifted by a day → different RW query


def test_same_day_rerun_is_stable():
    """Acceptance: same day → same scope (idempotent-by-file holds)."""
    base, n, day = "Sudan2026", 7, date(2026, 6, 3)
    assert date_stamped_project_name(base, day) == date_stamped_project_name(base, day)
    assert build_rw_url(rolling_window(day, n)) == build_rw_url(rolling_window(day, n))


def test_parse_window_roundtrip_and_validation():
    win = parse_window("20260315-20260321")
    assert win == IngestWindow(date(2026, 3, 15), date(2026, 3, 21))
    # end before start is rejected.
    with pytest.raises(ValueError):
        parse_window("20260321-20260315")
    # malformed specs are rejected.
    with pytest.raises(ValueError):
        parse_window("2026-03-15")
    with pytest.raises(ValueError):
        parse_window("notadate-20260321")


def test_parse_run_date():
    assert parse_run_date("20260321") == date(2026, 3, 21)
    with pytest.raises(ValueError):
        parse_run_date("2026-03-21")


def test_ingest_window_rejects_inverted_range():
    with pytest.raises(ValueError):
        IngestWindow(date(2026, 3, 21), date(2026, 3, 15))
