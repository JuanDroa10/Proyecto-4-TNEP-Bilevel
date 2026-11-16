"""Bound fixed-plan Heydari case-2 welfare under the Fig. 2 pixel error."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.heydari import load_heydari_garver
from tnep.models.fixed_plan_scipy import solve_fixed_plan


DELTA = 0.01


def shifted_case(base: dict, *, demand_delta: float = 0.0, wind_delta: float = 0.0) -> dict:
    case = dict(base)
    scenarios = []
    for original in base["scenarios"]:
        s = dict(original)
        s["demand_factors"] = {
            bus: float(value) + demand_delta
            for bus, value in original["demand_factors"].items()
        }
        s["wind_availability"] = {
            unit: min(1.0, max(0.0, float(value) + wind_delta))
            for unit, value in original["wind_availability"].items()
        }
        scenarios.append(s)
    case["scenarios"] = scenarios
    return case


def main() -> None:
    base = load_heydari_garver(2, weighting="duration_conditional")
    plan = base["published_plan"]
    variants = {
        "nominal": (0.0, 0.0),
        "load_minus_0p01": (-DELTA, 0.0),
        "load_plus_0p01": (DELTA, 0.0),
        "wind_minus_0p01": (0.0, -DELTA),
        "wind_plus_0p01": (0.0, DELTA),
        "joint_low_load_high_wind": (-DELTA, DELTA),
        "joint_high_load_low_wind": (DELTA, -DELTA),
    }
    results = {}
    for name, (load_delta, wind_delta) in variants.items():
        case = shifted_case(base, demand_delta=load_delta, wind_delta=wind_delta)
        results[name] = {
            "demand_factor_shift": load_delta,
            "wind_availability_shift": wind_delta,
            "market": solve_fixed_plan(case, plan),
        }
    out = Path("results/heydari_validation/heydari_fig2_digitization_sensitivity.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({
        name: {
            "expected_social_welfare_MUSD_per_year": item["market"]["expected_social_welfare_MUSD_per_year"],
            "max_load_shed_mw": max(item["market"]["scenario_load_shed_mw"].values()),
        }
        for name, item in results.items()
    }, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
