"""Solve the one-scenario-at-a-time classical cost baseline for Garces RTS-24."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.rts24 import load_rts24
from tnep.models.integrated_primal import solve_integrated, solve_market_for_fixed_plan


def main() -> None:
    case = load_rts24()
    results = []
    for scenario in case["scenarios"]:
        single_scenario_case = dict(case)
        single_scenario_case["scenarios"] = [{**scenario, "weight": 1.0}]
        minimum_cost = solve_integrated(
            single_scenario_case,
            objective_mode="classic_min_cost",
            reported_crf=True,
            time_limit_s=600,
        )
        market_clearing = solve_market_for_fixed_plan(case, minimum_cost["plan"])
        results.append({
            "scenario": scenario["name"],
            "plan": minimum_cost["plan"],
            "investment_MEUR": minimum_cost["investment_MEUR"],
            "scenario_social_welfare_MEUR_per_year": market_clearing[
                "scenario_social_welfare_MEUR_per_year"
            ][scenario["name"]],
            "average_social_welfare_MEUR_per_year": market_clearing[
                "expected_social_welfare_MEUR_per_year"
            ],
        })
    output = Path("results/garces_validation/rts24_no_contingencies_cost_min.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
