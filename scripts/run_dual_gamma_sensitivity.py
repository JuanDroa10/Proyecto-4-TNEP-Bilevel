"""Re-solve benchmark cases with a doubled dual bound Gamma=2000."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.garver import load_garver
from tnep.data.rts24 import load_rts24
from tnep.models.primal_dual import solve_primal_dual


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    baselines = {
        "garver6": ROOT / "results/garces_validation/garver_primal_dual.json",
        "rts24_no_contingencies": ROOT / "results/garces_validation/rts24_no_contingencies_primal_dual.json",
    }
    cases = {
        "garver6": load_garver(),
        "rts24_no_contingencies": load_rts24("no_contingencies"),
    }
    rows = []
    for name, case in cases.items():
        base = json.loads(baselines[name].read_text(encoding="utf-8"))
        sensitivity = solve_primal_dual(case, gamma_max=2000, time_limit_s=1800)
        rows.append({
            "case": name,
            "gamma_1000": base,
            "gamma_2000": sensitivity,
            "same_objective_within_1_eur": abs(base["objective_eur"] - sensitivity["objective_eur"]) < 1,
            "same_plan_by_corridor_and_count": sorted(
                (x["from_bus"], x["to_bus"]) for x in base["plan"]
            ) == sorted((x["from_bus"], x["to_bus"]) for x in sensitivity["plan"]),
        })
    output = ROOT / "results/garces_validation/dual_gamma_sensitivity.json"
    output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps([{
        "case": x["case"],
        "objective_1000_eur": x["gamma_1000"]["objective_eur"],
        "objective_2000_eur": x["gamma_2000"]["objective_eur"],
        "same_objective": x["same_objective_within_1_eur"],
        "same_plan_by_corridor_and_count": x["same_plan_by_corridor_and_count"],
        "saturated_duals_2000": x["gamma_2000"]["dual_values_at_gamma_max"],
    } for x in rows], indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
