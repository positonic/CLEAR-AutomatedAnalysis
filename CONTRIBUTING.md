# Contributing to CLEAR-AutomatedAnalysis

Thanks for helping. This repo turns ReliefWeb documents into a per-country **Situation Analysis**
following the NRC Situation Analysis Framework (SAF): it ingests reports, classifies entries with
HumBERT, runs LLM analysis over them, and writes the dashboard data. When configured, it also
publishes the result to clear-api, where the CLEAR platform's `/analysis` page reads it. The
[README](README.md) explains the pipeline stages; this file covers how to get set up and how to
get a change merged.

This repository is CLEAR's fork of
[MediaMonitoringAndAnalysis/CLEAR-AutomatedAnalysis](https://github.com/MediaMonitoringAndAnalysis/CLEAR-AutomatedAnalysis).
The libraries it builds on (`data_connectors`, `entry_extraction`,
`humanitarian_extract_classificator`, `llm_multiprocessing_inference`, `documents_processing`)
live in the [MediaMonitoringAndAnalysis](https://github.com/MediaMonitoringAndAnalysis)
organisation. A fix that belongs in one of those libraries should go there, not here.

## Two ways in

### Explore on your own

You need Python 3.11 (exactly; `pyproject.toml` pins `>=3.11,<3.12`) and
[uv](https://docs.astral.sh/uv/). The dependencies are heavy (PyTorch, transformers, HumBERT
models), so the first `uv sync` takes a while.

```bash
git clone https://github.com/positonic/CLEAR-AutomatedAnalysis.git
cd CLEAR-AutomatedAnalysis
uv sync            # installs runtime deps plus the dev group (pytest)
uv run pytest -q   # the unit tests need no API keys or network
```

To run the pipeline itself you need your own OpenAI API key. Put it in a `.env` file at the repo
root (the variable name is lowercase):

```bash
openai_api_key=sk-...
```

Then run one country end to end. `--sample_bool true` processes a small sample, which keeps a
first run cheap:

```bash
uv run clear-create-report-data --countries_to_analyze Sudan --sample_bool true
```

The run scrapes ReliefWeb for a rolling date window ending today, then writes everything under
`data/<project_name>_<YYYYMMDD>/` (gitignored) and the dashboard `.js` files under `src/viz/`.
`--run_date YYYYMMDD` or `--rw_date_range YYYYMMDD-YYYYMMDD` pins the window to replay an old run.
`uv run clear-create-report-data --help` lists every option.

> The README's "Running the Pipeline" section still describes the older two-command layout
> (`clear-create-entries` / `clear-generate-ui`). The single `clear-create-report-data` command
> above is what `pyproject.toml` defines today.

**What needs credentials from the team**

| Variable | What it's for | Without it |
| --- | --- | --- |
| `openai_api_key` | Every LLM step (analysis, numbers extraction, web-search context) | The pipeline can't run. Use your own key; the team doesn't share one. |
| `CLEAR_API_URL`, `PIPELINE_API_KEY` | Publishing the finished Situation Analysis to clear-api | Publishing is skipped with a `[publish]` log line. The dashboard files are still written. You can also point these at a clear-api you run yourself. |

`RW_INGEST_WINDOW_DAYS`, `RW_RUN_DATE`, `RW_DATE_RANGE` and `RW_COUNTRY_CODE` are optional
environment equivalents of the matching command-line flags.

### Join the team

1. Register at https://api.clearinitiative.io/portal/login.
2. The team will get in touch with next steps, including access to the tracker and any dev
   credentials you need. Credentials are shared privately.

Never ask for credentials in an issue or a pull request.

## Making a change

**Branches and PRs.** Branch off `main` and open your pull request against `main`. There are no
long-lived branches.

**Checks to run before pushing.** There is no CI workflow in this repo yet, so run the tests
locally:

```bash
uv run pytest -q
```

The tests cover the ingest window, the bundle assembler, the sources builder, the publisher and
the clear-api client. The LLM and HumBERT stages have no automated tests, so if you change them,
do a `--sample_bool true` run and say in the PR what you checked. New pure logic should come with
tests in `tests/`.

**Commit messages.** Recent history uses [Conventional Commits](https://www.conventionalcommits.org/):
`feat(ingest): …`, `feat(publish): …`, `fix: …`, `docs: …`, `chore: …`. Please follow the same style.

**Review.** A maintainer reviews and merges. Nothing merges automatically.

**The contract rule.** The bundle this pipeline publishes is read by clear-api and the CLEAR
frontend, so its shape is a shared contract (see
[ADR 0001](docs/adr/0001-situation-analysis-as-location-metadata.md)). Changes to it are
**additive only**: add new optional keys, never rename or remove one without coordinating with
the clear-api and frontend maintainers.

**Generated files.** Pipeline output under `data/` is gitignored. The dashboard data files under
`src/viz/` are checked in; only commit regenerated ones when your change is meant to update them.

**Where work is tracked.** Tickets live in Exponential (workspace `clear`, product `clear`), not
GitHub Issues, which are turned off on this repo. Team members get access after registering.

**Outside contributors.** Small fixes are welcome as pull requests. For anything bigger, register
first (see [Join the team](#join-the-team)) so it can be discussed before you build it.

## Secrets

- Never commit `.env` or any secret. `.env` and `.envrc` are gitignored.
- Never paste secret values into issues, PRs, chat or AI tools.
- If a secret leaks, tell the team immediately so it can be rotated.
- Credentials only ever come from the team, privately.

## Reporting a security issue

Don't open a public issue or PR. Report it privately through the CLEAR platform's vulnerability
reporting, which reaches the same team:
https://github.com/CLEAR-Initiative/clear-api/security/advisories/new (Security tab, then
"Report a vulnerability"). Say that it concerns CLEAR-AutomatedAnalysis.

## Licence

CLEAR-AutomatedAnalysis is licensed under the [GNU General Public License v3.0](./LICENSE),
inherited from the upstream project. Note that this differs from the AGPL-3.0 used by the other
CLEAR repos. By contributing, you agree your contribution is licensed the same way.
