import pandas as pd
from collections import Counter


# Ordered preference for quantifiers (most preferred first)
QUANTIFIER_PREFERENCE = [
    "More Than",
    "At Least",
    "Approximately",
    "Exact",
    "Less Than",
]

def _pick_preferred(values: list[str], preference: list[str], fallback_strategy="most_common") -> str:
    """
    Pick the best value from a list based on an ordered preference list.
    Falls back to most-common or first non-null value if none match.
    """
    non_null = [v for v in values if v and v != "-"]
    if not non_null:
        return "-"

    for preferred in preference:
        matches = [v for v in non_null if v.lower() == preferred.lower()]
        if matches:
            return matches[0]

    if fallback_strategy == "most_common":
        return Counter(non_null).most_common(1)[0][0]
    return non_null[0]


def _pick_min_date(dates: list[str], precisions: list[str]) -> tuple[str, str]:
    """Return the earliest valid date and its corresponding precision."""
    valid_pairs = [
        (d, p)
        for d, p in zip(dates, precisions)
        if d and d != "-"
    ]
    if not valid_pairs:
        return "-", "-"
    valid_pairs.sort(key=lambda x: x[0])
    return valid_pairs[0]


def _pick_max_date(dates: list[str], precisions: list[str]) -> tuple[str, str]:
    """Return the latest valid date and its corresponding precision."""
    valid_pairs = [
        (d, p)
        for d, p in zip(dates, precisions)
        if d and d != "-"
    ]
    if not valid_pairs:
        return "-", "-"
    valid_pairs.sort(key=lambda x: x[0], reverse=True)
    return valid_pairs[0]


def _pick_most_common_non_null(values: list[str]) -> str:
    non_null = [v for v in values if v and v != "-"]
    if not non_null:
        return "-"
    return Counter(non_null).most_common(1)[0][0]


def _pick_max_number(values: list) -> int | str:
    """Return the highest numeric value, or '-' if none are valid."""
    valid_numbers = []
    for value in values:
        if value in (None, "-"):
            continue
        try:
            valid_numbers.append(float(value))
        except (TypeError, ValueError):
            continue

    if not valid_numbers:
        return "-"

    max_value = max(valid_numbers)
    return int(max_value) if max_value.is_integer() else max_value


def _pick_row_with_max_number(group: pd.DataFrame) -> pd.Series:
    """Return the row with the highest valid numeric `number`."""
    numeric_numbers = pd.to_numeric(group["number"], errors="coerce")
    if numeric_numbers.notna().any():
        return group.loc[numeric_numbers.idxmax()]
    return group.iloc[0]


def merge_entries_by_number(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge rows by `what_happened` type and keep only the highest `number` per type:
      - number/unit:        taken from the row with the highest valid number in the type
      - what_happened:      group key
      - start_date:         earliest valid date; start_date_precision follows it
      - end_date:           latest valid date;   end_date_precision follows it
      - start_location:     most common non-null value
      - end_location:       most common non-null value
      - quantifier:         prefer "More Than" > "At Least" > "Approximately" > "Exact" > "Less Than"
      - risk_score:         maximum value across merged rows (if column present)
    """
    df = df.copy()
    # Normalise sentinel values
    df = df.fillna("-")

    rows = []
    for what_happened, group in df.groupby("what_happened", sort=False):
        max_row = _pick_row_with_max_number(group)
        merged: dict = {
            "number": _pick_max_number(group["number"].tolist()),
            "unit": max_row["unit"] if pd.notna(max_row["unit"]) and max_row["unit"] != "-" else "-",
            "what_happened": what_happened,
        }

        merged["start_date"], merged["start_date_precision"] = _pick_min_date(
            group["start_date"].tolist(),
            group["start_date_precision"].tolist(),
        )
        merged["end_date"], merged["end_date_precision"] = _pick_max_date(
            group["end_date"].tolist(),
            group["end_date_precision"].tolist(),
        )

        merged["start_location"] = _pick_most_common_non_null(group["start_location"].tolist())
        merged["end_location"] = _pick_most_common_non_null(group["end_location"].tolist())
        merged["quantifier"] = _pick_preferred(group["quantifier"].tolist(), QUANTIFIER_PREFERENCE)

        if "risk_score" in group.columns:
            valid_scores = [s for s in group["risk_score"].tolist() if str(s) != "-"]
            merged["risk_score"] = max(valid_scores) if valid_scores else "-"

        # Keep all source Entry IDs if present
        if "Entry ID" in group.columns:
            merged["Entry ID"] = list(group["Entry ID"].dropna().unique())

        rows.append(merged)

    return pd.DataFrame(rows).reset_index(drop=True)
