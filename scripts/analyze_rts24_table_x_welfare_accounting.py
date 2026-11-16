"""Recompute net and gross welfare for the published RTS-24 Table X plan.

This is an accounting diagnostic only. The market dispatch still includes the
100x lost-load penalty; gross welfare is reported to measure how much of the
published Table X value is explained by that term being omitted in reporting.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "garces_validation"
INPUT = RESULTS / "rts24_table_x_fixed_plan_diagnostic.json"
OUTPUT = RESULTS / "rts24_table_x_welfare_accounting_diagnostic.json"
PUBLISHED_WELFARE_MEUR_Y = 717.97


def main() -> None:
    fixed = json.loads(INPUT.read_text(encoding="utf-8"))["100"]
    with (ROOT / "data" / "processed" / "rts24_demands.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        demands = {row["demand"]: row for row in csv.DictReader(stream)}

    market = fixed["market"]
    weights = {
        scenario: float(row["weight"])
        for scenario, row in fixed["scenario_metadata"].items()
    } if "scenario_metadata" in fixed else None

    # Reconstruct the printed Table IX weights from the case definition.
    # Scenario 1 has weight 0.25; scenarios 2-22 have weight 0.0357.
    if weights is None:
        weights = {str(s): (0.25 if s == 1 else 0.0357) for s in range(1, 23)}

    weighted_penalty = 0.0
    weighted_net = 0.0
    for scenario, weight in weights.items():
        weighted_net += weight * float(
            market["scenario_social_welfare_MEUR_per_year"][scenario]
        )
        for demand, shed_mw in market["scenario_load_shed_by_demand_mw"][scenario].items():
            first_block_bid = float(demands[demand]["bid1_eur_mwh"])
            weighted_penalty += (
                weight * 100.0 * first_block_bid * float(shed_mw) * 8760.0 / 1e6
            )

    gross = weighted_net + weighted_penalty
    result = {
        "diagnostic_only": True,
        "interpretation": (
            "100x penalty remains in market dispatch; this recomputes gross welfare "
            "by adding back the weighted lost-load penalty after dispatch."
        ),
        "plan": fixed["plan"],
        "scenario_weight_sum_printed": sum(weights.values()),
        "net_welfare_MEUR_per_year": weighted_net,
        "weighted_load_shedding_penalty_MEUR_per_year": weighted_penalty,
        "gross_welfare_without_load_shedding_penalty_MEUR_per_year": gross,
        "published_table_X_welfare_MEUR_per_year": PUBLISHED_WELFARE_MEUR_Y,
        "net_error_percent": 100 * (weighted_net - PUBLISHED_WELFARE_MEUR_Y) / PUBLISHED_WELFARE_MEUR_Y,
        "gross_error_percent": 100 * (gross - PUBLISHED_WELFARE_MEUR_Y) / PUBLISHED_WELFARE_MEUR_Y,
        "source_aligned_metric": "net_welfare_MEUR_per_year",
        "warning": "Gross welfare is not the objective defined in Garces Eq. (1)/(5).",
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
