"""Build 30 approximate wind/load states digitized from Heydari Fig. 2."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ROOT / "data" / "uncertainty"
    load = pd.read_csv(source / "heydari_fig2_load_points.csv")
    wind = pd.read_csv(source / "heydari_fig2_wind_points.csv")
    states = wind.merge(load, on="load_block", validate="many_to_one")
    states["demand_multiplier"] = 2.2 * states["load_factor_pu"]
    states["wind_bus4_available_mw"] = 500 * states["wind_bus4_pu"]
    states["wind_bus6_available_mw"] = 500 * states["wind_bus6_pu"]
    states["weight_duration_times_conditional_wind"] = (
        states["duration_hours"] / 8760 * states["conditional_weight"]
    )
    states["weight_equal_over_all_30_states"] = 1 / len(states)
    states["scenario_id"] = states.apply(
        lambda row: f"L{int(row['load_block'])}_W{int(row['wind_state'])}", axis=1
    )
    out = source / "heydari_fig2_scenarios.csv"
    states.to_csv(out, index=False, float_format="%.8f")
    print(f"Wrote {out}")
    print(f"States: {len(states)}")
    print(f"Duration-weighted total: {states['weight_duration_times_conditional_wind'].sum():.10f}")
    print(f"Equal-state total: {states['weight_equal_over_all_30_states'].sum():.10f}")
    print("Weight interpretation is ambiguous in the article; retain both columns for sensitivity.")


if __name__ == "__main__":
    main()
