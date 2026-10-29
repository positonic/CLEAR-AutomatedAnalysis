# CLEAR — Automated Situation Analysis

**CLEAR** (Crisis-Led Evidence and Analysis for Response) is a pipeline that turns raw humanitarian documents into a fully interactive, downloadable situation analysis dashboard, following the [NRC Situation Analysis Framework (SAF)](https://www.nrc.no/).

---

## Pipeline Overview

```mermaid
flowchart LR
    A([ReliefWeb\nDocuments & PDFs]) --> B[Ingest · extract · classify\ncli/create_report_data.py]
    B --> C[(classification_dataset.csv)]
    C --> D[LLM Analysis\ndocuments_based_analysis.py]
    C --> E[Numbers Extraction\nnumbers_extraction.py]
    A2([Web Search]) --> F[Context Generation\ncontext_generation.py]
    D --> G[(answers.json\nrisk_list.json\nkey_indicator_numbers.json\npriority_needs.json\npriority_interventions.json\ninformation_coverage_gaps.json)]
    E --> H[(numbers_extraction.csv)]
    F --> I[(context_figures.json)]
    G & H & I --> J[Dashboard data\nsrc/analysis/generate_ui.py]
    J --> K[(JS data files\nsrc/viz/Country_src/)]
    K --> L([crisis_dashboard.html\nInteractive Dashboard])
    J --> M[Publish\npublisher.py]
    M --> N([clear-api\nSituation Analysis])
```

Every step runs from one command, `uv run clear-create-report-data` (see [Running the Pipeline](#running-the-pipeline)). The publish step only runs when `CLEAR_API_URL` and `PIPELINE_API_KEY` are set.

---

## Stage 1 — Build the analysis dataset

Ingests raw documents and produces structured analysis outputs (`cli/create_report_data.py`).

```mermaid
flowchart TD
    A[ReliefWeb scrape\nget_reliefweb_leads] --> B[Raw leads + PDF text\ndata/leads.csv]
    B --> C[Semantic Entry Extraction\n5-sentence sliding window\noverlap=2]
    C --> D[Entry-level dataset\nclassification_dataset.csv]
    D --> E{Already\nclassified?}
    E -- No --> F[HumBERT Classification\nhumbert_classification]
    F --> G[Tags: Pillars 1D · Pillars 2D · Sectors\nwith confidence scores]
    E -- Yes --> G
    G --> H{Per country\nloop}
    H --> I[documents_based_analysis\ngpt-4.1-mini · parallel prompts]
    H --> J[numbers_extraction\ngpt-4.1-mini · structured JSON]
    H --> K[context_generation\ngpt-5-mini · web search]
    I --> L[(answers.json\nrisk_list.json\nkey_indicator_numbers.json\npriority_needs.json\npriority_interventions.json\ninformation_coverage_gaps.json)]
    J --> M[(numbers_extraction.csv)]
    K --> N[(context_figures.json)]
```

### Entry Classification Tags

Each extracted entry is tagged across three dimensions simultaneously by HumBERT:

| Dimension | Tags |
|---|---|
| **Pillars 1D** | Displacement → Push/Pull/Intentions/Local Integration<br>Shock-Event → Type, Hazards, Underlying Factors, Mitigating Factors<br>Humanitarian Access → Constraints, Physical, Population↔Relief |
| **Pillars 2D** | Impact · Humanitarian Conditions · At Risk |
| **Sectors** | Agriculture · Education · Food Security · Health · Livelihoods · Logistics · Nutrition · Protection · Shelter · WASH |

### LLM Analysis — What the Model Produces

For every `(pillar/subpillar, sector)` combination that has relevant entries, a prompt is sent to `gpt-4.1-mini` with the top-N most relevant entries as context. Each response returns a structured JSON with five outputs:

```mermaid
flowchart LR
    P[LLM Prompt\ntopic + questions + context entries] --> R{Structured\nJSON response}
    R --> A1[answer\nnarrative text + relevance score]
    R --> A2[risk_list\nrisk name + severity 0–10 + source IDs]
    R --> A3[key_indicator_numbers\nmetric + value + unit + location + date]
    R --> A4[priority_needs\nneed description + score 0–10]
    R --> A5[priority_interventions\naction + score 0–10]
```

### Numbers Extraction

A separate pass runs `gpt-4.1-mini` specifically on entries tagged as containing casualty or displacement figures. Each number is extracted with full context:

```
number · unit · what_happened · start/end date+precision · start/end location · quantifier · risk_score
```

### Context Generation (Web-Search)

`context_generation.py` uses `gpt-5-mini` with live web search to answer 9 structural context questions per country (Demographics, Political, Economy, Socio-culture, Security, Legal & policy, Infrastructure, Environment, Humanitarian Coordination), producing `context_figures.json`.

---

## Stage 2 — Generate dashboard data

Reads all analysis JSON/CSV outputs and generates the JavaScript data files that power the dashboard (`src/analysis/generate_ui.py`, called at the end of each country's run). Each function applies severity filtering to keep only the most critical information.

```mermaid
flowchart TD
    subgraph Inputs
        A1[(answers.json)]
        A2[(risk_list.json)]
        A3[(key_indicator_numbers.json)]
        A4[(priority_needs.json)]
        A5[(priority_interventions.json)]
        A6[(numbers_extraction.csv)]
        A7[(context_figures.json)]
        A8[(classification_dataset.csv)]
        A9[(information_coverage_gaps.json)]
    end

    subgraph "JS Data Files → src/viz/Country_src/"
        B1[shown_risks_data.js\nSeverity matrix: Pillar 2D × Sector\nTop-3 risks per cell]
        B2[humanitarian_access_data.js\nAccess barriers with score ≥ 8]
        B3[key_sector_numbers_data.js\nCritical numbers: score ≥ 8, value > 100]
        B4[current_hazards_and_threats_data.js\nHazard & Threats subpillar]
        B5[precrisis_vulnerabilities_data.js\nUnderlying-Aggravating Factors]
        B6[displacement_risks_data.js\nTop-4 Push Factors & Intentions]
        B7[top_sectoral_needs_data.js\nNeeds with score ≥ 9, by sector]
        B8[top_priority_interventions_data.js\nInterventions with score ≥ 9, by sector]
        B9[displacement_data.js\nDisplacement counts: score ≥ 9]
        B10[final_numbers_data.js\nMax figures per event type: score ≥ 8]
        B11[top_5_sources_data.js\nMost-cited source documents]
        B12[output_context_risks_data.js\nContext risks with score ≥ 9]
        B13[information_coverage_data.js\nCoverage gaps per context pillar]
    end

    A2 --> B1
    A2 --> B2
    A2 --> B4
    A2 --> B5
    A2 --> B6
    A3 --> B2
    A3 --> B3
    A4 --> B7
    A5 --> B8
    A6 --> B9
    A6 --> B10
    A1 & A8 --> B11
    A7 --> B12
    A7 & A9 --> B13
```

### Severity Filter Logic

| Output | Threshold |
|---|---|
| Sector severity matrix | Max score per (Pillar 2D, Sector) pair, any score |
| Humanitarian access barriers | `risk_score ≥ 8` |
| Critical sector numbers | `risk_score ≥ 8` AND `number > 100` |
| Top sectoral needs | `priority_need_score ≥ 9` |
| Top priority interventions | `priority_intervention_score ≥ 9` |
| Displacement figures | `risk_score ≥ 9` AND `number > 100` |
| Final headline numbers | `risk_score ≥ 8` AND `number > 100` |
| Context risks | `risk_score ≥ 9` |

---

## Dashboard — `src/viz/crisis_dashboard.html`

A self-contained HTML file that loads the JS data files and renders three interactive tabs. No server required — open directly in a browser or share as a standalone file.

```mermaid
flowchart LR
    subgraph "📊 Overview Tab"
        O1[Headline KPIs\nKilled · Injured · Displaced]
        O2[Context Risks\nby pillar]
        O3[Hazards & Threats\nvs Pre-crisis Vulnerabilities]
        O4[Displacement Drivers\nvs Return Intentions]
    end

    subgraph "🏢 Sectors Tab"
        S1[Critical Numbers\nby sector]
        S2[Severity Matrix\nImpact · Conditions · At Risk\nper sector, with tooltip top-3 risks]
        S3[Top Needs\nby sector]
    end

    subgraph "🔮 Response Planning Tab"
        R1[Humanitarian Access Barriers]
        R2[Priority Interventions\nby sector]
    end
```

The dashboard supports **country switching** (Lebanon / Sudan) and a **one-click PDF export** that renders all three tabs into a print-ready document.

---

## Repository Structure

```
CLEAR-AutomatedAnalysis/
├── cli/
│   ├── create_report_data.py        # The whole pipeline  →  uv run clear-create-report-data
│   └── ingest_window.py             # Rolling ReliefWeb date window + date-stamped run folder
│
├── src/
│   ├── analysis/
│   │   ├── analytical_questions.py  # All SAF pillar/subpillar question definitions
│   │   ├── documents_based_analysis.py  # LLM prompting & output parsing
│   │   ├── numbers_extraction.py    # Structured numerical data extraction
│   │   ├── context_generation.py    # Web-search context generation
│   │   ├── merge_numbers.py         # Number deduplication logic
│   │   ├── generate_ui.py           # Stage 2: dashboard data generation
│   │   ├── bundle_assembler.py      # Dashboard structures → publishable bundle
│   │   ├── sources_builder.py       # Cited sources enriched from the leads
│   │   ├── publisher.py             # Archives source PDFs, upserts the bundle to clear-api
│   │   └── clear_api_client.py      # GraphQL client for clear-api
│   └── viz/
│       ├── crisis_dashboard.html    # Interactive dashboard
│       └── {Country}_src/*.js       # Generated data files (output of Stage 2)
│
├── tests/                           # pytest unit tests (no keys or network needed)
│
└── data/                            # gitignored
    └── {ProjectName}_{YYYYMMDD}/
        ├── leads.csv                # Raw document metadata
        ├── classification_dataset.csv   # Entries + HumBERT tags
        ├── pdf_files/               # Downloaded PDF documents
        └── analysis/
            └── {Country}/
                ├── answers.json
                ├── risk_list.json
                ├── key_indicator_numbers.json
                ├── priority_needs.json
                ├── priority_interventions.json
                ├── information_coverage_gaps.json
                ├── numbers_extraction.csv
                ├── context_figures.json
                └── shown_risks.json
```

---

## Running the Pipeline

**Prerequisites:** Python 3.11 and [uv](https://docs.astral.sh/uv/). Set `openai_api_key` in a `.env` file at the repo root.

Install dependencies (this includes the dev group, so `uv run pytest -q` runs the tests):

```bash
uv sync
```

### Run the pipeline

One command runs every stage: ReliefWeb ingest, entry extraction, HumBERT classification, LLM analysis, numbers extraction, context generation, dashboard data, and (optionally) publishing to clear-api.

```bash
uv run clear-create-report-data --sample_bool true
```

That scrapes ReliefWeb for Sudan over the last 7 days and writes to `data/Sudan2026_<YYYYMMDD>/`. Drop `--sample_bool true` for a full run.

| Argument | Default | Description |
|---|---|---|
| `--project_name` | `Sudan2026` | Name of the project / data subfolder; `_YYYYMMDD` is appended unless `--date_stamp_project false` |
| `--countries_to_analyze` | `Sudan` | Comma-separated list of countries to analyse |
| `--rw_country_code` | `C220` (Sudan) | ReliefWeb country code used for the ingest search |
| `--ingest_window_days` | `7` | Length of the rolling ReliefWeb window ending on the run date |
| `--run_date` | today | Pin the run date as `YYYYMMDD` to replay an old run |
| `--rw_date_range` | — | Pin an explicit window as `YYYYMMDD-YYYYMMDD` |
| `--n_kept_entries` | `12` | Max entries per analysis prompt (higher = richer but slower) |
| `--sample_bool` | `false` | `true` uses a small sample for testing |

`uv run clear-create-report-data --help` lists every option. `RW_INGEST_WINDOW_DAYS`, `RW_RUN_DATE`, `RW_DATE_RANGE` and `RW_COUNTRY_CODE` are environment equivalents of the matching flags.

Each sub-step is **idempotent** — if the output file already exists it is skipped. Because each run gets a date-stamped folder, resume an interrupted run by passing its `--run_date`.

### Publish to clear-api (optional)

Set `CLEAR_API_URL` and `PIPELINE_API_KEY` and the run upserts each country's Situation Analysis to clear-api and archives the cited source PDFs (see [ADR 0001](docs/adr/0001-situation-analysis-as-location-metadata.md)). Without them the publish step is skipped with a `[publish]` log line; the dashboard files are still written.

### View the dashboard

Open `src/viz/crisis_dashboard.html` directly in any browser. It loads each country's data from the `{Country}_src/` folder next to it.

---

## External Dependencies

| Library | Role |
|---|---|
| `entry_extraction` | Semantic sliding-window entry segmentation |
| `humanitarian_extract_classificator` | HumBERT multilingual entry classification |
| `data_connectors` | ReliefWeb scraping + PDF text extraction |
| `llm_multiprocessing_inference` | Parallel LLM calls with structured output parsing |
| `openai` | GPT-4.1-mini (analysis) + GPT-5-mini with web search (context) |

---

## What's Next

See [`next-steps.md`](next-steps.md) for planned improvements, including NLP model retraining on multilingual data, recommended actions, forecasting, and scenario modelling.

---

## Contributing

How to get set up, the PR workflow, and where work is tracked: see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Licensed under the GNU General Public License v3.0. See [`LICENSE`](./LICENSE) for the full text.
