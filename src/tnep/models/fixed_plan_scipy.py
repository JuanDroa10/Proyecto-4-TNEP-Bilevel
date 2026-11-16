"""Independent LP market clearing for a fixed transmission expansion plan.

This uses SciPy/HiGHS without Pyomo and matches the continuous fixed-plan
subproblem in integrated_primal.py. It does not optimize investment decisions.
Inactive candidate circuits have zero flow and retain the original big-M
angle inequalities. Active circuits satisfy DC flow equations and limits.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog


def _clear_scenario(case: dict, selected: set[tuple[int, int, int]], scenario: dict) -> dict:
    generators = case["generators"]
    wind_units = case.get("wind_units", [])
    demands = case["demands"]
    p = case["parameters"]
    keys: list[tuple] = []
    bounds: list[tuple[float, float]] = []
    costs: list[float] = []

    def variable(key: tuple, lower: float, upper: float, cost: float) -> None:
        keys.append(key)
        bounds.append((lower, upper))
        costs.append(cost)

    for g in generators:
        for b in (1, 2, 3):
            variable(("gen", g["unit"], b), 0, float(g[f"block{b}_mw"]),
                     float(g[f"offer{b}_eur_mwh"]))
    for w in wind_units:
        variable(("wind", w["unit"]), 0,
                 float(w["capacity_mw"]) * float(scenario["wind_availability"][w["unit"]]),
                 float(w.get("offer_price_mwh", 0)))
    for d in demands:
        factor = float(scenario["demand_factors"][int(d["bus"])])
        for b in (1, 2, 3):
            variable(("demand", d["demand"], b), 0, float(d[f"block{b}_mw"]) * factor,
                     -float(d[f"bid{b}_eur_mwh"]))
        variable(("shed", d["demand"]), 0,
                 factor * sum(float(d[f"block{b}_mw"]) for b in (1, 2, 3)),
                 float(p.get("load_shedding_penalty_multiplier", 100)) * float(d["bid1_eur_mwh"]))
    for bus in case["buses"]:
        slack = int(bus) == int(case["slack_bus"])
        variable(("theta", int(bus)), 0 if slack else -np.pi,
                 0 if slack else np.pi, 0)

    active = []
    inactive = []
    outage = scenario.get("line_outage")
    for line in case["lines"]:
        i, j = int(line["from_bus"]), int(line["to_bus"])
        existing = int(line["existing_circuits"])
        max_total = int(line["max_total_circuits"])
        for c in range(1, max_total + 1):
            if c <= existing:
                enabled = not (outage is not None and tuple(sorted((i, j))) == tuple(sorted(outage)))
            else:
                enabled = (i, j, c - existing) in selected
            if enabled:
                active.append((i, j, c, line))
                cap = float(line["capacity_mw"])
                variable(("flow", i, j, c), -cap, cap, 0)
            else:
                inactive.append((i, j, c, line))

    indices = {key: k for k, key in enumerate(keys)}
    a_eq, b_eq, a_ub, b_ub = [], [], [], []
    for bus in case["buses"]:
        bus = int(bus)
        row = np.zeros(len(keys))
        for g in generators:
            if int(g["bus"]) == bus:
                for b in (1, 2, 3):
                    row[indices[("gen", g["unit"], b)]] += 1
        for w in wind_units:
            if int(w["bus"]) == bus:
                row[indices[("wind", w["unit"])]] += 1
        for d in demands:
            if int(d["bus"]) == bus:
                row[indices[("shed", d["demand"])]] += 1
                for b in (1, 2, 3):
                    row[indices[("demand", d["demand"], b)]] -= 1
        for i, j, c, _ in active:
            if i == bus:
                row[indices[("flow", i, j, c)]] -= 1
            if j == bus:
                row[indices[("flow", i, j, c)]] += 1
        a_eq.append(row)
        b_eq.append(0)

    for i, j, c, line in active:
        row = np.zeros(len(keys))
        row[indices[("flow", i, j, c)]] = 1
        susceptance = float(case["base_mva"]) / float(line["reactance_pu"])
        row[indices[("theta", i)]] = -susceptance
        row[indices[("theta", j)]] = susceptance
        a_eq.append(row)
        b_eq.append(0)

    for d in demands:
        row = np.zeros(len(keys))
        for b in (1, 2, 3):
            row[indices[("demand", d["demand"], b)]] = -1
        factor = float(scenario["demand_factors"][int(d["bus"])])
        minimum = float(d["minimum_fraction"]) * factor * sum(
            float(d[f"block{b}_mw"]) for b in (1, 2, 3))
        a_ub.append(row)
        b_ub.append(-minimum)

    # The Pyomo model uses ±M even when a circuit is off. Retaining these
    # angle inequalities makes the independent LP match that exact model.
    big_m = float(p["big_m_angle"])
    for i, j, _, line in inactive:
        susceptance = float(case["base_mva"]) / float(line["reactance_pu"])
        row = np.zeros(len(keys))
        row[indices[("theta", i)]] = susceptance
        row[indices[("theta", j)]] = -susceptance
        a_ub.append(row)
        b_ub.append(big_m)
        a_ub.append(-row)
        b_ub.append(big_m)

    result = linprog(costs, A_ub=np.asarray(a_ub), b_ub=np.asarray(b_ub),
                     A_eq=np.asarray(a_eq), b_eq=np.asarray(b_eq),
                     bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(f"Market LP {scenario['name']}: {result.message}")

    x = result.x
    shed_by_demand = {
        str(d["demand"]): float(x[indices[("shed", d["demand"])]] )
        for d in demands if x[indices[("shed", d["demand"])]] > 1e-7
    }
    loading = []
    for i, j, c, line in active:
        f = float(x[indices[("flow", i, j, c)]])
        if abs(f) > 1e-7:
            cap = float(line["capacity_mw"])
            loading.append({"from_bus": i, "to_bus": j, "circuit": c,
                            "flow_mw": f, "capacity_mw": cap,
                            "loading_percent": 100 * abs(f) / cap})
    return {
        "welfare_per_hour": -float(result.fun),
        "shed_mw": sum(shed_by_demand.values()),
        "shed_by_demand_mw": shed_by_demand,
        "thermal_generation_mw": sum(float(x[indices[("gen", g["unit"], b)]])
                                     for g in generators for b in (1, 2, 3)),
        "wind_generation_mw": sum(float(x[indices[("wind", w["unit"])]]) for w in wind_units),
        "consumption_mw": sum(float(x[indices[("demand", d["demand"], b)]])
                              for d in demands for b in (1, 2, 3)),
        "circuit_loading": sorted(loading, key=lambda item: item["loading_percent"], reverse=True),
    }


def solve_fixed_plan(case: dict, plan: list[dict]) -> dict:
    """Maximize market welfare for each scenario with a fixed network plan."""
    selected = {(int(x["from_bus"]), int(x["to_bus"]), int(x["slot"])) for x in plan}
    if len(selected) != len(plan):
        raise ValueError("Duplicate circuit in plan")
    valid = {
        (int(l["from_bus"]), int(l["to_bus"]), c)
        for l in case["lines"]
        for c in range(1, int(l["max_total_circuits"]) - int(l["existing_circuits"]) + 1)
    }
    if not selected <= valid:
        raise ValueError(f"Plan contains unknown circuit slots: {sorted(selected - valid)}")
    scenarios = case["scenarios"]
    solved = {str(s["name"]): _clear_scenario(case, selected, s) for s in scenarios}
    currency = case.get("welfare_currency", "EUR")
    annual_hours = float(case["parameters"]["annual_hours_sigma"])
    return {
        f"scenario_social_welfare_M{currency}_per_year": {
            name: value["welfare_per_hour"] * annual_hours / 1e6
            for name, value in solved.items()},
        "scenario_load_shed_mw": {name: value["shed_mw"] for name, value in solved.items()},
        "scenario_load_shed_by_demand_mw": {
            name: value["shed_by_demand_mw"] for name, value in solved.items()},
        "scenario_thermal_generation_mw": {
            name: value["thermal_generation_mw"] for name, value in solved.items()},
        "scenario_wind_generation_mw": {
            name: value["wind_generation_mw"] for name, value in solved.items()},
        "scenario_consumption_mw": {
            name: value["consumption_mw"] for name, value in solved.items()},
        "scenario_circuit_loading": {
            name: value["circuit_loading"] for name, value in solved.items()},
        f"expected_social_welfare_M{currency}_per_year": sum(
            float(s["weight"]) * solved[str(s["name"])]["welfare_per_hour"] * annual_hours / 1e6
            for s in scenarios),
        "solver": "SciPy HiGHS linprog (independent fixed-plan LP)",
    }
