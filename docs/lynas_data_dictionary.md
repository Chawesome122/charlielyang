# Added empirical tables

All paths below are under `data/processed/rare_earths_additional/`. Source keys join `metadata/additional_rare_earth_sources.csv`; its `archive_path` and SHA256 identify original bytes. `info_public_date` is a verified issuer-index release date, not necessarily the first discoverable release. No field denotes an independently verified stable qualified capacity unless explicitly stated.

| Table | Keys and content | Interpretation |
|---|---|---|
| `lynas_project_history.csv` | `claim_id`; persistent `project_id`/`activity_id`; stage and reported state; `valid_date`; nullable event bounds; source page/quote/hash; separate target bounds/quote | A/F/I/C/Q/O/S/X vocabulary follows the blueprint. First production remains Q when stable operation is unverified. A dated snapshot does not impute a state-entry day. All rows remain inadmissible to a population hazard risk set. |
| `lynas_quarterly_production_versions.csv` | `observation_id`; quarter/product; source release; integer native value; source unit token; `comparative`; report-period end; locator/hash | One row per explicitly labelled highlights cell. Later comparative columns do not become earlier public observations. Product-family and total REO values must not be summed together. |
| `lynas_quarterly_production_asof_freeze.csv` | quarter/product; latest source-public clock at freeze | Deduplicated view of the version table, not an overwrite of it. Native tonnes are neither element mass nor delivered magnet tonnes. |
| `lynas_quarterly_annual_reconciliation.csv` | fiscal year/product; quarterly sum; own-year annual value; difference; pass flag | Only four-quarter-complete years are compared. A match is internal issuer consistency, not independent verification. |
| `lynas_documented_material_links.csv` | route/source key; upstream/downstream node; commodity; event bounds and public clock | Records observed feed introduction or dispatch. Route capacity and recovery remain null. China-free inputs and commercial network readiness are false/unverified. |

The codebook `codebooks/lynas_project_milestones.csv` is a hand-adjudicated specification with exact-page matching expressions; it is not independently double-coded. Stage `separation` includes the Kalgoorlie cracking/leaching intermediate activity, explicitly identified by its product form; it is never treated as separated oxide capacity.

Baseline outputs under `outputs/empirical/rare_earths/` preserve the origin, next-quarter target, prediction, eventual observed value, selected source IDs and maximum training-public date for each method. Scores use native-product tonnes. They describe eight dependent common origins per product within this archive subset; they are not forecasts of physical service or calibrated transition probabilities.
