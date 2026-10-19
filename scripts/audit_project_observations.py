"""Quantify source-visible histories without constructing false survival spells."""
import json
from pathlib import Path

import pandas as pd

from weaponized.rare_earths.history import disclosure_inventory, state_pair_audit

ROOT = Path(__file__).resolve().parents[1]


def main():
    frame = pd.read_csv(ROOT/"data/processed/rare_earths/project_state_evidence.csv")
    pairs = state_pair_audit(frame)
    inventory = disclosure_inventory(frame)
    out = ROOT/"data/processed/project_histories"
    pairs.to_csv(out/"state_pair_audit.csv", index=False)
    inventory.to_csv(out/"quarterly_disclosure_inventory.csv", index=False)
    report = dict(passed=True, observed_pairs=len(pairs), pair_classes=pairs.pair_class.value_counts().to_dict(),
                  pairs_missing_event_windows=int(pairs.missing_event_window.sum()),
                  overlapping_or_revised_pairs=int(pairs.overlapping_or_revised_windows.sum()),
                  quarterly_disclosure_origins=len(inventory), final_origin=inventory.iloc[-1].origin_date,
                  first_exit_spells_admissible=int(pairs.first_exit_likelihood_admissible.sum()),
                  physically_observed_risk_inventory_available=False,
                  no_news_interpretation="unknown physical state/survival, not right-censored no-exit exposure",
                  population_transition_estimates_available=False)
    (ROOT/"outputs/diagnostics/project_observation_audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
