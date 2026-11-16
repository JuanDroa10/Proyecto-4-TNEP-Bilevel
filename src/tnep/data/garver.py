"""Load the transcribed Garver tables and attach explicit model settings."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]


def load_garver() -> dict:
    data_dir = ROOT / "data" / "processed"
    lines = pd.read_csv(data_dir / "garver_lines.csv").to_dict("records")
    generators = pd.read_csv(data_dir / "garver_generators.csv").to_dict("records")
    demands = pd.read_csv(data_dir / "garver_demands.csv").to_dict("records")
    scenario_rows = pd.read_csv(data_dir / "garver_scenarios.csv").to_dict("records")
    parameters = json.loads((data_dir / "garver_parameters.json").read_text(encoding="utf-8"))

    scenarios = []
    for row in scenario_rows:
        factors = {
            bus: float(row[f"bus_{bus}_factor"])
            for bus in range(1, 7)
        }
        scenarios.append({
            "name": str(row["scenario"]),
            "weight": float(row["weight"]),
            "demand_factors": factors,
            "line_outage": None,
        })
    return {
        "name": "garver6",
        "lines": lines,
        "generators": generators,
        "demands": demands,
        "scenarios": scenarios,
        "parameters": parameters,
        "buses": list(range(1, 7)),
        "slack_bus": 1,
        "base_mva": float(parameters["network_base_mva"]),
    }
