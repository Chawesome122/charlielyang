# Weaponizing Interdependence

Executed research software and an evidence-limited manuscript on U.S.-led semiconductor controls, Chinese rare-earth restrictions, and induced adaptation. **Information freeze: 2026-10-11.** The scientific authority is the supplied 49-page [master blueprint](references/master_blueprint.pdf). Its complete reading aid is [master_blueprint.txt](references/master_blueprint.txt).

This repository contains actual primary-source archives, extracted observations, tested mathematical modules, executed scenario results, and explicit failed checks. **It does not contain a calibrated forecast of China-free magnet service, a causal estimate of technological substitution, a valid headline historical SPOI, or a certified continuous-state Markov-perfect equilibrium.** Read [RESEARCH_STATUS.md](RESEARCH_STATUS.md) and [the requirement audit](audit/blueprint_requirements.csv) before interpreting outputs.

## Reproduce

Requirements: Python 3.12, uv **0.12.23**, `pdftotext` (Poppler), and `latexmk`/pdfLaTeX with standard LaTeX recommended/extra packages. The resolved Python dependency versions and artifact hashes are in `uv.lock`. Install uv from its official package if absent: `python -m pip install uv==0.12.23` in an appropriate isolated environment.

From this repository's root:

```bash
uv sync --frozen
uv run python scripts/restore_omitted_sources.py --fetch
uv run python scripts/replicate.py
```

The default command rebuilds the empirical tables, primary-source checks, synthetic physical/ODE and 10,000-path forecast experiments, descriptive empirical baselines, figures, manuscript and final manifest. It independently reloads and tests the saved large-game solutions, rather than recomputing those large solves. After the omitted NBER original is restored, no research-source network access is needed for replication. The other archived inputs are included. In this cloud workspace, `UV_CACHE_DIR=/workspace/.cache/uv` avoids writing outside the allowed directories.

To **recompute the game solves too**, including all six positive-response starts at 17⁴ and 21⁴ nodes, negative/zero response checks, the alternate failed negative solver, and the smaller-grid policy scenarios:

```bash
uv run python scripts/replicate.py --full
```

The validated full clean-container run took about 23 minutes; the expanded default rebuild took about 106 seconds on this instance. Runtime depends on CPU and BLAS settings. The script sets numerical-library thread counts to one to avoid costly oversubscription. It records each command's underlying exit status and log. A numerical experiment reporting `not_solved` is an expected scientific outcome; its policies do not become accepted equilibria because the reporting script exits successfully.

Individual checks:

```bash
uv run pytest -q
uv run python scripts/build_rare_earths.py
uv run python scripts/fetch_additional_rare_earths.py  # cached original reports, no refresh
uv run python scripts/build_lynas_history.py
uv run python scripts/build_industrial_evidence.py
uv run python scripts/build_mp_investment.py
uv run python scripts/build_project_histories.py
uv run python scripts/build_project_registry.py
uv run python scripts/audit_project_observations.py
uv run python scripts/build_evidence_coverage.py
uv run python scripts/run_semiconductors.py
uv run python scripts/discover_legal.py
uv run python scripts/review_legal_discovery.py
uv run python scripts/run_opacity.py
uv run python scripts/run_physical.py
uv run python scripts/run_forecast.py --draws 10000
uv run python scripts/run_empirical_baselines.py
uv run python scripts/audit_game.py
uv run python scripts/report.py
cd manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

`--no-pdf` skips only PDF compilation on machines without TeX. `make reproduce` and `make reproduce-full` use the local `.venv` created by uv. Do not change the dependency lock during replication.

## Clean container

`Dockerfile` pins an actually retrieved Python 3.12.14 image by registry digest and pins uv. Building requires public OS/Python package access; running the research can be disconnected:

```bash
docker build -t weaponized-research .
docker run --rm --network none weaponized-research
```

This runs full recomputation inside the image. To retain its generated outputs, create a named container, run it, then `docker cp CONTAINER:/app/outputs ./container_outputs` and `docker cp CONTAINER:/app/manuscript/main.pdf ./container_manuscript.pdf` before removing it. Current-host container validation is not an independent second-machine replication. The exact validation outcome is in `outputs/diagnostics/`.

A Git clone omits the full NBER paper under its explicit quotation/reprint terms. Before source-integrity validation or a Docker build, obtain that one original directly from its publisher:

```bash
uv run python scripts/restore_omitted_sources.py --fetch
```

The command verifies the recorded digest and never substitutes a newer revision. It needs network access only when the original is missing. If acquisition fails, source-integrity replication remains blocked for that original. The full local-source and clean-container checks recorded here had that source available. See `THIRD_PARTY_NOTICES.md`; the project's MIT license does not relicense external documents.

In this cloud environment, use the tested builder to forward the existing proxy route and its provided public CA while preserving TLS verification:

```bash
uv run python scripts/build_container.py
DOCKER_CONFIG="$PWD/.cache/docker" docker run --name weaponized-replication --network none weaponized-research python scripts/container_check.py
```

The second command additionally compares regenerated primary-data tables and selected 17⁴/21⁴ policy/value arrays to the supplied results. Use a new container name if one with that name already exists. No proxy credentials or CA values are printed or embedded in research configuration.

## Evidence and interpretation

- `data/raw/`: original bytes, hashes and attempted acquisition records; no private-account data. Some HTTP 200 responses are challenge pages and are explicitly excluded from claims.
- `data/processed/rare_earths/`: immutable-source-linked KPI versions and a documented subset of project states. Fiscal year-end, event interval, verified public availability and retrieval time are distinct. A SEC filing date is a conservative verified availability date, not proof that no earlier press release existed.
- `data/processed/rare_earths_additional/`: Lynas 2016–2026 annual native-product output, backed by issuer-index timestamps and original reports. Product-family tonnes are not contained element or magnet tonnes.
- `data/processed/semiconductors/`: selected original legal-event phases, exact supporting legal excerpts, and SMIC reported investment inputs. The legal corpus is not a fully consolidated current-law database. Licensing is not prohibition; spending is not capability.
- `outputs/empirical/`: actual reported descriptive evidence and explicit missingness/identification audits. Two MP mine-output baseline comparisons are descriptive exercises, not evidence of forecast calibration or a global project model.
- `outputs/synthetic/`: engineering fixtures and simulations with invented, explicitly registered test inputs. Their probabilities are **not real-world forecasts**.
- `outputs/scenario/game/`: hypothetical payoff/adaptation scenarios. Each archive has policy/value arrays, residuals, best-response/deviation checks and mesh diagnostics. Fine-grid negative-response failures and nonzero off-grid continuum residuals are retained.
- `outputs/diagnostics/empirical_forecast_targets.csv`: the requested 2028Q4/2031Q4/2035Q4 × four threshold entries, with probabilities missing and exact blocking requirements.
- `manuscript/main.tex`, `main.pdf`: the academic draft and technical appendices. `claims.json` links its principal claims to generated evidence files.
- `metadata/claims_to_sources.csv`, source manifests, `outputs/run_manifest.json`: traceability and checksums.
- `audit/blueprint_requirements.csv`: requirement-by-requirement VERIFIED/PARTIAL/BLOCKED/NOT ATTEMPTED assessment.

## Acquire or extend sources

Normal replication preserves archived vintages. Live retrieval is a separate operation and may produce new versions; never overwrite an old claim with a revised value. `scripts/fetch.py --retry-failures`, `scripts/run_semiconductors.py --fetch`, `scripts/fetch_literature.py`, and `scripts/fetch_additional_rare_earths.py --refresh` record actual successes and failures. New research information after the freeze must be quarantined until a separately authorized new frozen release.

`uv run python scripts/discover_legal.py` rebuilds the additional cached legal-discovery registry. Its two date-limited BIS queries identify 58 candidates, of which 21 documents now match the reviewed corpus. `uv run python scripts/review_legal_discovery.py` verifies scope screening for all 41 additional archived originals: four add five reviewed phases; eight are procedural; the remaining records require item/entity mapping or remain other policy context. The complete corpus has 27 phases and is not consolidated current law. `--fetch` refreshes query artifacts and `--fetch-texts` acquires missing originals. Discovery matches never automatically become access-loss or capability measures.

`uv run python scripts/build_lynas_revisions.py` reproduces the separate observed-revision table. The main Lynas series retains each fiscal year's own annual-report values. The FY2017 report gives FY2016 comparatives of 3896 NdPr / 12631 total-REO tonnes, versus 3897/12630 in the original FY2016 report; both versions are retained, and the cause of the discrepancy is not assumed. This is not an exhaustive restatement audit.

`uv run python scripts/build_lynas_history.py` checks 23 milestone claims and extracts 66 quarterly source-vintage cells. `uv run python scripts/run_lynas_baselines.py` produces eight-origin publication-safe comparisons. Both run in the main replication pipeline. The reported Texas cancellation and retrospectively disclosed Mountain Pass cold-idle/relaunch remain in the roster. Six quarter/annual reconciliations match exactly; see `docs/lynas_history_review.md` and `outputs/diagnostics/lynas_history_validation.json`.

`uv run python scripts/build_industrial_evidence.py` checks eight more downstream milestone records and five technical claims. With the history extension below, the combined roster is now 60 records/24 projects/32 activities. The Energy Fuels finite-batch disclosure reports approximately 1.2 tonnes of oxide processed into 3.0 tonnes of magnets; this is not annual capacity or complete China-free service. `uv run python scripts/build_evidence_coverage.py` generates per-activity flags, stage coverage counts and a figure. It finds 31 source-public clocks and 11 native annual capacity mentions; missing industrial recipes, route limits, independent sustained qualification and demand still block physical service estimation. See `docs/industrial_evidence_review.md` and `outputs/empirical/rare_earths/finite_batch_evidence.json`.

The archived SEC MP company-facts extension supplies 53 cash-PPE filing versions over 28 overlapping reported durations. Six first-half totals and three exact quarter/half-year reconciliations are regenerated by `scripts/build_mp_investment.py`. These nominal consolidated financial inputs do not measure project capacity or policy effects. Eight new issuer requests and three exact Q2 2026 original SEC filings failed at the proxy; source logs and the review memo retain precise pointers and missing corroboration. No inaccessible filing text is presented as read.

`scripts/build_project_histories.py` preserves 15 RER milestone/target versions from three archived SEC filings, including changed construction-completion years, operating targets and a commissioning pause. `scripts/audit_project_observations.py` audits 28 observed state pairs and produces 44 quarterly source-disclosure origins. Physical risk counts and survival exposures remain missing: no news is not observed survival, and repeated snapshots are not independent transitions. See [the history review](docs/project_history_review.md), `data/processed/project_histories/` and the reproducible Upton vintage figure. The additional RER Q2 2026 original request also failed with CONNECT 403; its exact filing pointer is retained.

Required source hosts are recorded in acquisition manifests and the environment configuration. Some agency/CDN downloads remain denied or unavailable. Restricted/commercial data must be supplied legally; a URL, an API account requirement, or a blueprint assertion is not an acquired dataset. Access terms for each publisher remain relevant. The continuation request authorizes Git push; no journal submission or external research review is implied.

## Resume unfinished research

Use this isolated checkout; do not create a worktree. Begin with `RESEARCH_STATUS.md`, `PLANS.md`, the audit, and `docs/`. The next empirical milestone is to finish the inclusive project universe and stage/element/feed/route/demand constraints, obtain engineering review of fixed semiconductor targets and qualified milestones, and establish dated opacity obligations and blinded independent coding. These inputs are needed before fitting population hazards or empirical game adaptation parameters. National utility/payoff coefficients remain scenario assumptions.
