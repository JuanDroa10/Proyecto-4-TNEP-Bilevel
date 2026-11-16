"""Evaluate every saved expansion plan under the SAME five load states.

The original method objectives use different approximate distributions and
cannot be compared directly as realized plan quality. This independent LP
check uses the five-state load-duration distribution as a common reference.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tnep.data.garver import load_garver
from tnep.models.fixed_plan_scipy import solve_fixed_plan


def evaluate_all() -> list[dict]:
    stored = json.loads((ROOT / "results/uncertainty/garver_demand_method_comparison.json").read_text())
    loads = pd.read_csv(ROOT / "data/uncertainty/heydari_fig2_load_points.csv")
    case = load_garver()
    case["scenarios"] = [
        {"name": f"L{int(r.load_block)}", "weight": float(r.duration_hours) / 8760,
         "demand_factors": {bus: float(r.load_factor_pu) for bus in case["buses"]},
         "wind_availability": {}, "line_outage": None}
        for r in loads.itertuples()
    ]
    evaluated = []
    for item in stored:
        optimization = item["optimization"]
        market = solve_fixed_plan(case, optimization["plan"])
        welfare = market["expected_social_welfare_MEUR_per_year"]
        investment_annual = float(optimization["investment_eur"]) * float(optimization["crf"]) / 1e6
        evaluated.append({
            "method": item["method"],
            "plan": optimization["plan"],
            "objective_on_own_scenarios_MEUR_per_year": float(optimization["objective_eur"]) / 1e6,
            "common_reference": "the original five load-duration states and duration_hours/8760 weights",
            "common_expected_social_welfare_MEUR_per_year": welfare,
            "annualized_investment_MEUR_per_year": investment_annual,
            "common_net_objective_MEUR_per_year": welfare - investment_annual,
            "per_state_social_welfare_MEUR_per_year_if_full_year": market[
                "scenario_social_welfare_MEUR_per_year"],
            "per_state_load_shed_mw": market["scenario_load_shed_mw"],
            "solver": market["solver"],
        })
    reference = evaluated[0]["common_net_objective_MEUR_per_year"]
    if abs(reference - stored[0]["optimization"]["objective_eur"] / 1e6) > 1e-5:
        raise AssertionError("Independent fixed-plan reference does not match saved five-state optimum")
    for row in evaluated:
        row["regret_vs_five_state_optimum_MEUR_per_year"] = reference - row["common_net_objective_MEUR_per_year"]
    output = ROOT / "results/uncertainty/garver_common_evaluation.json"
    output.write_text(json.dumps(evaluated, indent=2), encoding="utf-8")
    return evaluated


if __name__ == "__main__":
    for row in evaluate_all():
        print(f"{row['method']}: common net {row['common_net_objective_MEUR_per_year']:.6f} "
              f"M€/year; regret {row['regret_vs_five_state_optimum_MEUR_per_year']:.6f} M€/year")
