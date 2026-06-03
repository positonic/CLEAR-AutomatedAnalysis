from ast import literal_eval
import pandas as pd
from data_connectors import get_reliefweb_leads
from src.analysis.documents_based_analysis import _perform_documents_based_analysis
from src.analysis.numbers_extraction import performs_numbers_extraction
from src.analysis.context_generation import generate_context
from src.analysis.generate_ui import generate_dashboard_data
from src.analysis.sources_builder import build_sources
from src.analysis.clear_api_client import ClearApiClient
from src.analysis.publisher import publish_situation_analysis, pdf_loader_from_dir
from cli.ingest_window import (
    DEFAULT_COUNTRY_CODE,
    DEFAULT_WINDOW_DAYS,
    build_rw_url,
    date_stamped_project_name,
    parse_run_date,
    parse_window,
    rolling_window,
)
import argparse
import dotenv
import os
from datetime import date
from typing import Dict

dotenv.load_dotenv()

openai_api_key = os.getenv("openai_api_key")


def _extract_entries(
    leads: pd.DataFrame,
    text_column: str = "text",
    entries_column: str = "Extraction Text",
) -> pd.DataFrame:

    from entry_extraction import SemanticEntriesExtractor

    extractor = SemanticEntriesExtractor(max_sentences=5, overlap=2)
    entries = extractor(leads[text_column].tolist())
    if isinstance(entries[0], dict):
        entries_text = [entry["text"] for entry in entries]
    else:
        entries_text = entries
    # entries_page_number = [entry["page"] for entry in entries]
    leads[entries_column] = entries_text
    # leads[entries_page_number_column] = entries_page_number
    leads = leads.explode(entries_column)
    leads = leads.drop_duplicates(subset=[entries_column])
    leads = leads[leads[entries_column].apply(lambda x: len(str(x)) > 3)].drop(columns=[text_column])
    return leads


def _classify_entries(
    entries: pd.DataFrame,
    entries_column: str = "Extraction Text",
    classification_column: str = "First Level Classification",
    prediction_ratio: float = 1.05,
    return_ratio: bool = True,
) -> pd.DataFrame:
    from humanitarian_extract_classificator import humbert_classification

    entries[classification_column] = humbert_classification(
        entries[entries_column].tolist(),
        prediction_ratio=prediction_ratio,
        return_ratio=return_ratio,
    )
    return entries


def _preprocess_classification_results(classification_results: str) -> Dict[str, float]:
    # number_tags = {
    #     "Pillars 2D->At Risk->Number Of People At Risk": "Pillars 2D->At Risk->Risk And Vulnerabilities",
    #     "Pillars 2D->Impact->Number Of People Affected": "Pillars 2D->Impact->Impact On People",
    #     "Pillars 2D->Humanitarian Conditions->Number Of People In Need": "Pillars 2D->Humanitarian Conditions->Living Standards",
    # }
    classification_results_dict = literal_eval(classification_results)
    # final_classification = {}
    # for tag in classification_results_list:
    #     if tag in number_tags:
    #         final_classification[number_tags[tag]] = classification_results_list[tag]
    #     else:
    #         final_classification[tag.replace(
    #                 "Pillars 2D->Priority Interventions", "Pillars 2D->Priority Needs"
    #             )
    #         ] = classification_results_list[tag]
    return classification_results_dict


def _import_classification_dataset(
    classification_dataset_path: str,
    classification_column: str = "First Level Classification",
) -> pd.DataFrame:
    df = pd.read_csv(classification_dataset_path)
    df[classification_column] = df[classification_column].apply(
        _preprocess_classification_results
    )
    df = df.sort_values(by="Extraction Text", key=lambda col: col.fillna("").str.len())
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample_bool", type=str, default="false")
    parser.add_argument("--project_name", type=str, default="Sudan2026")
    parser.add_argument("--text_column", type=str, default="text")
    parser.add_argument("--entries_column", type=str, default="Extraction Text")
    parser.add_argument(
        "--classification_column", type=str, default="First Level Classification"
    )
    parser.add_argument("--prediction_ratio", type=float, default=1.05)
    parser.add_argument(
        "--countries_to_analyze", type=str, nargs="+", default="Sudan"
    )
    parser.add_argument("--n_kept_entries", type=int, default=12)
    parser.add_argument("--answers_save_path", type=str, default="answers.json")
    parser.add_argument("--risk_list_save_path", type=str, default="risk_list.json")
    parser.add_argument(
        "--key_indicator_numbers_save_path",
        type=str,
        default="key_indicator_numbers.json",
    )
    parser.add_argument(
        "--priority_needs_save_path", type=str, default="priority_needs.json"
    )
    parser.add_argument(
        "--priority_interventions_save_path",
        type=str,
        default="priority_interventions.json",
    )
    parser.add_argument("--model_name", type=str, default="gpt-4.1-nano")

    # ── Rolling ReliefWeb ingest window + date-stamped run scope ──
    parser.add_argument(
        "--ingest_window_days",
        type=int,
        default=int(os.getenv("RW_INGEST_WINDOW_DAYS", DEFAULT_WINDOW_DAYS)),
        help="Length (days) of the rolling RW window ending on the run date.",
    )
    parser.add_argument(
        "--run_date",
        type=str,
        default=os.getenv("RW_RUN_DATE"),
        help="Pin the run date as YYYYMMDD (default: today). Drives both the "
        "window end and the date stamp — pass an old date to replay a run.",
    )
    parser.add_argument(
        "--rw_date_range",
        type=str,
        default=os.getenv("RW_DATE_RANGE"),
        help="Pin an explicit RW window as YYYYMMDD-YYYYMMDD, overriding the "
        "rolling window (for exact reproducibility of an old run).",
    )
    parser.add_argument(
        "--rw_country_code",
        type=str,
        default=os.getenv("RW_COUNTRY_CODE", DEFAULT_COUNTRY_CODE),
        help="ReliefWeb country code for the advanced-search filter.",
    )
    parser.add_argument(
        "--date_stamp_project",
        type=str,
        default="true",
        help="Append _YYYYMMDD to project_name so each run gets a fresh "
        "folder. Set false to pin the exact folder name for a replay.",
    )
    args = parser.parse_args()

    sample = args.sample_bool.lower() == "true"

    # Resolve the ingest window + run scope from the run date (or pins).
    run_date = parse_run_date(args.run_date) if args.run_date else date.today()
    if args.rw_date_range:
        window = parse_window(args.rw_date_range)
    else:
        window = rolling_window(run_date, args.ingest_window_days)
    rw_url = build_rw_url(window, args.rw_country_code)
    project_name = (
        date_stamped_project_name(args.project_name, run_date)
        if args.date_stamp_project.lower() == "true"
        else args.project_name
    )
    print(
        f"[ingest] RW window {window.rw_param()} ({window.days}d) "
        f"→ project '{project_name}'"
    )

    leads_df = get_reliefweb_leads(
        project_page_starting_url=rw_url,
        project_name=project_name,
        data_folder="data",
        extracted_data_path=os.path.join("data", project_name, "leads.csv"),
        openai_api_key=openai_api_key,  # falls back to OPENAI_API_KEY env var
        extract_pdf_text=True,
        save=True,
        sample=sample,
        model_name=args.model_name,
    )

    classification_dataset_path = os.path.join(
        "data", project_name, "classification_dataset.csv"
    )

    if not os.path.exists(classification_dataset_path):
        entries_df = _extract_entries(
            leads_df, text_column=args.text_column, entries_column=args.entries_column
        )
        entries_df.to_csv(classification_dataset_path, index=False)
    else:
        entries_df = pd.read_csv(classification_dataset_path)

    if args.classification_column not in entries_df.columns:
        entries_df = _classify_entries(
            entries_df,
            classification_column=args.classification_column,
            prediction_ratio=args.prediction_ratio,
        )
        entries_df.to_csv(classification_dataset_path, index=False)

    if "Entry ID" not in entries_df.columns:
        entries_df["Entry ID"] = entries_df.index
        entries_df.to_csv(classification_dataset_path, index=False)

    save_folder = os.path.join("data", project_name, "analysis")
    classification_df = _import_classification_dataset(
        classification_dataset_path, args.classification_column
    )
    for country in args.countries_to_analyze.split(","):
        one_country_classification_df = classification_df[
            classification_df["Primary Country"].apply(lambda x: country in x)
        ]
        _perform_documents_based_analysis(
            one_country_classification_df,
            country,
            args.classification_column,
            args.n_kept_entries,
            os.path.join(save_folder, country),
            args.answers_save_path,
            args.risk_list_save_path,
            args.key_indicator_numbers_save_path,
            args.priority_needs_save_path,
            args.priority_interventions_save_path,
        )
        numbers_extraction_df_path = os.path.join(save_folder, country, "numbers_extraction.csv")
        performs_numbers_extraction(
            one_country_classification_df,
            numbers_extraction_df_path,
        )

        generate_context(country, os.path.join(save_folder, country, "context_figures.json"))

        bundle = generate_dashboard_data(
            data_folder=f"data/{project_name}/analysis/{country}/",
            viz_folder=f"src/viz/{country}_src/",
            country=country,
            project_name=project_name,
        )

        # Enrich sources from the cited names + leads, then publish the bundle
        # to clear-api when a pipeline key is configured. The standalone `.js`
        # files above are always written regardless.
        bundle["sources"] = build_sources(bundle.get("top_5_sources") or [], leads_df)
        _publish_bundle(country, bundle, project_name)


def _publish_bundle(country: str, bundle: dict, project_name: str) -> None:
    """Publish the assembled bundle to clear-api if CLEAR_API_URL +
    PIPELINE_API_KEY are set; otherwise skip (dashboard `.js` files still
    written). Failures are logged, never fatal to the run."""
    base_url = os.getenv("CLEAR_API_URL")
    api_key = os.getenv("PIPELINE_API_KEY")
    if not base_url or not api_key:
        print(
            f"[publish] CLEAR_API_URL / PIPELINE_API_KEY not set — skipping "
            f"clear-api publish for {country} (dashboard .js still written)."
        )
        return
    try:
        client = ClearApiClient(base_url, api_key)
        pdf_dir = os.path.join("data", project_name, "pdf_files")
        result = publish_situation_analysis(
            client,
            country,
            bundle,
            source_pdf_loader=pdf_loader_from_dir(pdf_dir),
        )
        print(
            f"[publish] {country}: location {result['locationId']}, "
            f"{result['archived']} source PDF(s) archived, bundle upserted."
        )
    except Exception as exc:  # noqa: BLE001 — publishing must not fail the run
        print(f"[publish] WARNING: failed to publish {country}: {exc}")


if __name__ == "__main__":
    main()
