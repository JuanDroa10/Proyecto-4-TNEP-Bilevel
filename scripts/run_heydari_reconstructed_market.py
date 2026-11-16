"""Market-clearing check for published Heydari HVAC-only Garver plans.

This does not optimize investments and is explicitly an approximate
reconstruction from Garces' HVAC data and digitized Heydari Fig. 2.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.heydari import load_heydari_garver
from tnep.models.fixed_plan_scipy import solve_fixed_plan


def investment_proxy_meur(case: dict, plan: list[dict]) -> float:
    lines = {(int(x["from_bus"]), int(x["to_bus"])): x for x in case["lines"]}
    cost_k_eur = sum(
        float(lines[(int(x["from_bus"]), int(x["to_bus"]))]["investment_kEUR"])
        for x in plan
    )
    return cost_k_eur / 1000


def main() -> None:
    results = []
    reference = pd.read_csv(Path("data/uncertainty/heydari_garver_reference_results.csv"))
    for case_number in (1, 2):
        weightings = ["duration_conditional"] if case_number == 1 else ["duration_conditional", "equal_30"]
        for weighting in weightings:
            case = load_heydari_garver(case_number, weighting=weighting)
            market = solve_fixed_plan(case, case["published_plan"])
            welfare_key = "expected_social_welfare_MUSD_per_year"
            published = float(reference.loc[reference["case"] == case_number, "expected_social_welfare_MUSD"].iloc[0])
            reproduced = float(market[welfare_key])
            results.append({
                "case": case_number,
                "weighting_interpretation": weighting,
                "published_hvac_plan": case["published_plan"],
                "garces_cost_proxy_MEUR": investment_proxy_meur(case, case["published_plan"]),
                "reconstructed_market": market,
                "published_expected_social_welfare_MUSD_per_year": published,
                "reconstructed_minus_published_MUSD_per_year": reproduced - published,
                "relative_error_percent": 100 * (reproduced - published) / abs(published),
                "investment_optimization": "not performed; EUR Garces costs and USD Heydari welfare are not combined",
                "reproduction_status": "approximate fixed-plan market check only",
            })
    output = Path("results/heydari_validation/heydari_garver_reconstructed_market.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
