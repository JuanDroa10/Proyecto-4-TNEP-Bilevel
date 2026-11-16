"""Clear the RTS-24 multi-contingency market at the published Table X plan."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.rts24 import load_rts24
from tnep.models.integrated_primal import solve_market_for_fixed_plan


PLAN = [
    {"from_bus": 3, "to_bus": 9, "slot": 1},
    {"from_bus": 6, "to_bus": 10, "slot": 1},
    {"from_bus": 7, "to_bus": 8, "slot": 1},
    {"from_bus": 7, "to_bus": 8, "slot": 2},
    {"from_bus": 10, "to_bus": 11, "slot": 1},
    {"from_bus": 11, "to_bus": 13, "slot": 1},
    {"from_bus": 13, "to_bus": 14, "slot": 1},
]


def main() -> None:
    result = {}
    for penalty in (100, 10):
        case = load_rts24("multicontingency", load_shedding_multiplier=penalty)
        started = time.perf_counter()
        market = solve_market_for_fixed_plan(case, PLAN)
        key = "expected_social_welfare_MEUR_per_year"
        result[str(penalty)] = {
            "plan": PLAN,
            "penalty_multiplier": penalty,
            "market": market,
            "scenario_weight_sum": sum(s["weight"] for s in case["scenarios"]),
            "wall_time_s": time.perf_counter() - started,
        }
    output = Path("results/garces_validation/rts24_table_x_fixed_plan_diagnostic.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        k: {
            "penalty": v["penalty_multiplier"],
            "expected_social_welfare_MEUR_per_year": v["market"]["expected_social_welfare_MEUR_per_year"],
            "max_shed_mw": max(v["market"]["scenario_load_shed_mw"].values()),
            "scenario_22_welfare_MEUR_per_year": v["market"]["scenario_social_welfare_MEUR_per_year"]["22"],
            "scenario_22_shed_mw": v["market"]["scenario_load_shed_mw"]["22"],
            "wall_time_s": v["wall_time_s"],
        } for k, v in result.items()
    }, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
