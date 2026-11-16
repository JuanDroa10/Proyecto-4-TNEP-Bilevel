"""Build a clearly labeled Garces-network reconstruction of Heydari Garver."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from tnep.data.garver import ROOT


def reference_plan(case_number: int, case: dict) -> list[dict]:
    """Read Table 4 HVAC additions and expand them into build-slot indices."""
    if case_number not in (1, 2):
        raise ValueError("The published cases 3-4 require unavailable HVDC line parameters")
    source = ROOT / "data" / "uncertainty" / "heydari_garver_reference_results.csv"
    matches = pd.read_csv(source).query("case == @case_number")
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one Table 4 row for case {case_number}")
    entries = str(matches.iloc[0]["hvac_plan"]).split(";")
    counts = {}
    for entry in entries:
        match = re.fullmatch(r"\s*(\d+)-(\d+)\((\d+)\)\s*", entry)
        if not match:
            raise ValueError(f"Invalid Table 4 HVAC entry: {entry!r}")
        i, j, n = (int(part) for part in match.groups())
        key = (i, j)
        if key in counts:
            raise ValueError(f"Duplicate corridor in Table 4: {key}")
        counts[key] = n
    line_map = {
        (int(line["from_bus"]), int(line["to_bus"])): line
        for line in case["lines"]
    }
    plan = []
    for key, count in counts.items():
        if key not in line_map:
            raise ValueError(f"Corridor missing from reconstructed HVAC network: {key}")
        line = line_map[key]
        existing = int(line["existing_circuits"])
        if count > int(line["max_total_circuits"]) - existing:
            raise ValueError(f"Published additions exceed available build slots on {key}")
        plan.extend({"from_bus": key[0], "to_bus": key[1], "slot": s} for s in range(1, count + 1))
    return plan


def load_heydari_garver(case_number: int, *, weighting: str = "duration_conditional") -> dict:
    """Load case 1 or 2 using Garces HVAC data and digitized Fig. 2 profiles.

    This is an approximate reconstruction, not the authors' original dataset.
    No HVDC alternative is synthesized; cases 3-4 therefore remain unavailable.
    """
    if case_number not in (1, 2):
        raise ValueError("Only Heydari cases 1-2 can be reconstructed without HVDC input data")
    if weighting not in ("duration_conditional", "equal_30"):
        raise ValueError("weighting must be 'duration_conditional' or 'equal_30'")

    processed = ROOT / "data" / "processed"
    uncertain = ROOT / "data" / "uncertainty"
    garver_lines = pd.read_csv(processed / "garver_lines.csv").to_dict("records")
    garver_generators = pd.read_csv(processed / "garver_generators.csv").to_dict("records")
    garver_demands = pd.read_csv(processed / "garver_demands.csv").to_dict("records")
    prices = pd.read_csv(uncertain / "heydari_garver_market_prices.csv").set_index("bus")
    profile = pd.read_csv(uncertain / "heydari_fig2_scenarios.csv")
    params = json.loads((uncertain / "heydari_garver_parameters.json").read_text(encoding="utf-8"))

    generators = []
    for row in garver_generators:
        bus = int(row["bus"])
        market_prices = prices.loc[bus]
        g = {
            "bus": bus,
            "unit": str(row["unit"]),
            "source": row["source"],
        }
        for b in range(1, 4):
            g[f"block{b}_mw"] = float(row[f"block{b}_mw"])
            g[f"offer{b}_eur_mwh"] = float(market_prices[f"generator_offer{b}_usd_mwh"])
        generators.append(g)

    if case_number == 1:
        for row in pd.read_csv(uncertain / "heydari_case1_thermal_units.csv").to_dict("records"):
            generators.append({
                "bus": int(row["bus"]), "unit": str(row["unit"]),
                "block1_mw": float(row["block1_mw"]),
                "block2_mw": float(row["block2_mw"]),
                "block3_mw": float(row["block3_mw"]),
                "offer1_eur_mwh": float(row["offer1_usd_mwh"]),
                "offer2_eur_mwh": float(row["offer2_usd_mwh"]),
                "offer3_eur_mwh": float(row["offer3_usd_mwh"]),
            })

    demands = []
    for row in garver_demands:
        bus = int(row["bus"])
        market_prices = prices.loc[bus]
        d = {
            "bus": bus,
            "demand": str(row["demand"]),
            "minimum_fraction": 0.9,
            "source": row["source"],
        }
        for b in range(1, 4):
            d[f"block{b}_mw"] = float(row[f"block{b}_mw"]) * float(params["demand_coefficient"])
            d[f"bid{b}_eur_mwh"] = float(market_prices[f"demand_bid{b}_usd_mwh"])
        demands.append(d)

    lines = []
    for row in garver_lines:
        line = dict(row)
        line["max_total_circuits"] = 4
        lines.append(line)

    scenarios = []
    if case_number == 1:
        loads = pd.read_csv(uncertain / "heydari_fig2_load_points.csv")
        for row in loads.to_dict("records"):
            scenarios.append({
                "name": f"L{int(row['load_block'])}",
                "weight": float(row["duration_hours"]) / 8760,
                "demand_factors": {bus: float(row["load_factor_pu"]) for bus in range(1, 7)},
                "wind_availability": {},
                "line_outage": None,
            })
        wind_units = []
    else:
        wind_units = [
            {"unit": "W4", "bus": 4, "capacity_mw": 500, "offer_price_mwh": 0.0},
            {"unit": "W6", "bus": 6, "capacity_mw": 500, "offer_price_mwh": 0.0},
        ]
        weight_column = (
            "weight_duration_times_conditional_wind"
            if weighting == "duration_conditional"
            else "weight_equal_over_all_30_states"
        )
        for row in profile.to_dict("records"):
            scenarios.append({
                "name": str(row["scenario_id"]),
                "weight": float(row[weight_column]),
                "demand_factors": {bus: float(row["load_factor_pu"]) for bus in range(1, 7)},
                "wind_availability": {
                    "W4": float(row["wind_bus4_pu"]),
                    "W6": float(row["wind_bus6_pu"]),
                },
                "line_outage": None,
            })

    settings = {
        "annual_hours_sigma": 8760,
        "investment_budget_kEUR": 400000,
        "minimum_demand_fraction": 0.9,
        "load_shedding_penalty_multiplier": 10,
        "interest_rate": 0.1,
        "investment_lifetime_years": 25,
        "capital_recovery_factor_report_reproduction": 0.1,
        "big_m_angle": 1000,
        "gamma_max_dual": 1000,
        "network_base_mva": 100,
        "transcription_status": "approximate HVAC reconstruction; EUR Garces capex and USD Heydari market prices kept distinct",
    }
    return {
        "name": f"heydari_garver_case{case_number}_reconstructed",
        "lines": lines,
        "generators": generators,
        "demands": demands,
        "wind_units": wind_units,
        "scenarios": scenarios,
        "parameters": settings,
        "buses": list(range(1, 7)),
        "slack_bus": 1,
        "base_mva": 100.0,
        "welfare_currency": "USD",
        "investment_currency": "EUR",
        "investment_optimization_allowed": False,
        "weighting_interpretation": weighting if case_number == 2 else "duration_blocks",
        "published_plan": reference_plan(case_number, {"lines": lines}),
    }
