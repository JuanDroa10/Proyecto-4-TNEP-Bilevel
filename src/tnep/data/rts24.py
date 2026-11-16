"""Load Garces' RTS-24 network appendix and market case tables."""
from __future__ import annotations

import json

import pandas as pd
from pathlib import Path

from tnep.data.garver import ROOT


def load_rts24(case_name: str = "no_contingencies", *, load_shedding_multiplier: float = 100) -> dict:
    data_dir = ROOT / "data" / "processed"
    lines = pd.read_csv(data_dir / "rts24_lines.csv").to_dict("records")
    generators = pd.read_csv(data_dir / "rts24_generators.csv").to_dict("records")
    demands = pd.read_csv(data_dir / "rts24_demands.csv").to_dict("records")
    common = json.loads((data_dir / "rts24_parameters.json").read_text(encoding="utf-8"))
    def make_scenario(number: int, weight: float, groups: list[tuple[float, list[int]]], outage=None):
        factors = {bus: 1.0 for bus in range(1, 25)}
        for factor, buses in groups:
            for bus in buses:
                factors[bus] = factor
        return {"name": str(number), "weight": weight, "demand_factors": factors, "line_outage": outage}

    all_buses = list(range(1, 25))
    zone_sw = [1, 3, 4, 5, 9]
    zone_se = [2, 6, 7, 8, 10]
    zone_nw = [15, 16, 18]
    zone_ne = [13, 14, 19, 20]
    scenarios = []
    if case_name == "no_contingencies":
        scenarios = [
            make_scenario(1, 0.50, []),
            make_scenario(2, 0.25, [(1.1, list(range(1, 11)))]),
            make_scenario(3, 0.25, [(1.2, list(range(11, 25)))]),
        ]
    elif case_name == "multicontingency":
        # Table IX weights are printed to four decimal places: 0.25 and 0.0357.
        # Preserve those values in the baseline; normalized weights are a sensitivity.
        w = 0.0357
        scenarios = [
            make_scenario(1, 0.25, []),
            make_scenario(2, w, [(1.1, zone_sw), (1.2, zone_se)]),
            make_scenario(3, w, [(1.1, zone_se)]),
            make_scenario(4, w, [(1.2, zone_ne)]),
            make_scenario(5, w, [(1.2, zone_nw)]),
            make_scenario(6, w, [(1.1, list(range(1, 11)))]),
            make_scenario(7, w, [(1.1, zone_sw), (1.2, zone_ne)]),
            make_scenario(8, w, [(1.1, zone_sw), (1.2, zone_nw)]),
            make_scenario(9, w, [(1.1, zone_se), (1.2, zone_ne)]),
            make_scenario(10, w, [(1.1, zone_se), (1.2, zone_nw)]),
            make_scenario(11, w, [(1.2, list(range(11, 25)))]),
            make_scenario(12, w, [(1.1, list(range(1, 11))), (1.2, zone_ne)]),
            make_scenario(13, w, [(1.1, list(range(1, 11))), (1.2, zone_nw)]),
            make_scenario(14, w, [(1.1, zone_sw), (1.2, list(range(11, 25)))]),
            make_scenario(15, w, [(1.1, zone_se), (1.2, list(range(11, 25)))]),
            make_scenario(16, w, [(1.1, list(range(1, 11))), (1.2, list(range(11, 25)))]),
        ]
        for n, outage in enumerate([(11,13), (11,14), (12,13), (12,23), (14,16), (15,24)], start=17):
            scenarios.append(make_scenario(n, w, [], outage=outage))
    else:
        raise ValueError("case_name must be 'no_contingencies' or 'multicontingency'")

    parameters = {
        "annual_hours_sigma": common["annual_hours_sigma"],
        "investment_budget_kEUR": common[
            "investment_budget_no_contingencies_MEUR" if case_name == "no_contingencies"
            else "investment_budget_multicontingency_MEUR"
        ] * 1000,
        "minimum_demand_fraction": common["minimum_demand_fraction"],
        "load_shedding_penalty_multiplier": load_shedding_multiplier,
        "interest_rate": common["interest_rate"],
        "investment_lifetime_years": common["investment_lifetime_years"],
        "capital_recovery_factor_report_reproduction": common["capital_recovery_factor_report_reproduction"],
        "big_m_angle": 1000,
        "gamma_max_dual": 1000,
    }
    return {
        "name": f"rts24_garces_{case_name}",
        "lines": lines,
        "generators": generators,
        "demands": demands,
        "scenarios": scenarios,
        "parameters": parameters,
        "buses": list(range(1, 25)),
        "slack_bus": 13,
        "base_mva": 100.0,
    }
