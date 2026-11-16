"""Primal integrated MILP equivalent for aligned Garces objectives.

Each market scenario maximizes declared social welfare, and the upper level
maximizes the same weighted scenario welfare minus annualized investment.
Because market scenarios are independent conditional on a common network
plan, optimizing all primal dispatch variables jointly is equivalent to
imposing each follower's optimal value. This is a useful reference MILP;
the separate primal-dual/strong-duality implementation remains required for
the requested formulation traceability.
"""
from __future__ import annotations

import math

import pyomo.environ as pyo


def capital_recovery_factor(rate: float, years: int, reported_approximation: bool = True) -> float:
    if reported_approximation:
        return 0.1
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)


def build_integrated_model(
    case: dict,
    *,
    reported_crf: bool = True,
    objective_mode: str = "aligned_welfare",
) -> pyo.ConcreteModel:
    p = case["parameters"]
    buses = case["buses"]
    lines = case["lines"]
    generators = case["generators"]
    wind_units = case.get("wind_units", [])
    demands = case["demands"]
    scenarios = case["scenarios"]
    sigma = float(p["annual_hours_sigma"])
    base_mva = float(case["base_mva"])
    big_m = float(p["big_m_angle"])
    load_shedding_multiplier = float(p.get("load_shedding_penalty_multiplier", 100))
    crf = capital_recovery_factor(
        float(p["interest_rate"]), int(p["investment_lifetime_years"]), reported_crf
    )

    line_keys = [(int(l["from_bus"]), int(l["to_bus"])) for l in lines]
    line_by_key = {key: line for key, line in zip(line_keys, lines)}
    scenario_names = [s["name"] for s in scenarios]
    gen_keys = [(g["unit"], block) for g in generators for block in range(1, 4)]
    wind_keys = [w["unit"] for w in wind_units]
    demand_keys = [(d["demand"], block) for d in demands for block in range(1, 4)]
    candidate_keys = [
        (key, slot)
        for key, line in zip(line_keys, lines)
        for slot in range(1, int(line["max_total_circuits"]) - int(line["existing_circuits"]) + 1)
    ]

    m = pyo.ConcreteModel(name=f"{case['name']}_integrated_primal")
    m.S = pyo.Set(initialize=scenario_names, ordered=True)
    m.N = pyo.Set(initialize=buses, ordered=True)
    m.K = pyo.Set(dimen=2, initialize=line_keys, ordered=True)
    m.C = pyo.Set(dimen=3, initialize=[(k[0], k[1], c) for k, c in candidate_keys], ordered=True)
    m.GB = pyo.Set(dimen=2, initialize=gen_keys, ordered=True)
    m.W = pyo.Set(initialize=wind_keys, ordered=True)
    m.DB = pyo.Set(dimen=2, initialize=demand_keys, ordered=True)

    m.build = pyo.Var(m.C, domain=pyo.Binary)
    m.generation = pyo.Var(m.S, m.GB, domain=pyo.NonNegativeReals)
    m.wind_generation = pyo.Var(m.S, m.W, domain=pyo.NonNegativeReals)
    m.consumption = pyo.Var(m.S, m.DB, domain=pyo.NonNegativeReals)
    m.shed = pyo.Var(m.S, [d["demand"] for d in demands], domain=pyo.NonNegativeReals)
    m.theta = pyo.Var(m.S, m.N, bounds=(-math.pi, math.pi))

    # One flow variable for each existing circuit and each potential new circuit.
    circuit_keys = []
    for key, line in zip(line_keys, lines):
        circuit_keys.extend((key[0], key[1], c) for c in range(1, int(line["max_total_circuits"]) + 1))
    m.LC = pyo.Set(dimen=3, initialize=circuit_keys, ordered=True)
    m.flow = pyo.Var(m.S, m.LC, domain=pyo.Reals)

    def gen_cap_rule(m, s, unit, block):
        g = next(g for g in generators if g["unit"] == unit)
        return m.generation[s, unit, block] <= float(g[f"block{block}_mw"])
    m.gen_cap = pyo.Constraint(m.S, m.GB, rule=gen_cap_rule)

    def wind_cap_rule(m, s, unit):
        wind = next(w for w in wind_units if w["unit"] == unit)
        available_pu = float(next(x for x in scenarios if x["name"] == s)["wind_availability"][unit])
        return m.wind_generation[s, unit] <= float(wind["capacity_mw"]) * available_pu
    m.wind_cap = pyo.Constraint(m.S, m.W, rule=wind_cap_rule)

    def demand_cap_rule(m, s, demand, block):
        d = next(d for d in demands if d["demand"] == demand)
        factor = float(next(x for x in scenarios if x["name"] == s)["demand_factors"][int(d["bus"])])
        return m.consumption[s, demand, block] <= float(d[f"block{block}_mw"]) * factor
    m.demand_cap = pyo.Constraint(m.S, m.DB, rule=demand_cap_rule)

    def min_demand_rule(m, s, demand):
        d = next(d for d in demands if d["demand"] == demand)
        factor = float(next(x for x in scenarios if x["name"] == s)["demand_factors"][int(d["bus"])])
        total = sum(float(d[f"block{b}_mw"]) for b in range(1, 4)) * factor
        return sum(m.consumption[s, demand, b] for b in range(1, 4)) >= float(d["minimum_fraction"]) * total
    m.min_demand = pyo.Constraint(m.S, [d["demand"] for d in demands], rule=min_demand_rule)

    def shed_cap_rule(m, s, demand):
        d = next(d for d in demands if d["demand"] == demand)
        factor = float(next(x for x in scenarios if x["name"] == s)["demand_factors"][int(d["bus"])])
        return m.shed[s, demand] <= sum(float(d[f"block{b}_mw"]) for b in range(1, 4)) * factor
    m.shed_cap = pyo.Constraint(m.S, [d["demand"] for d in demands], rule=shed_cap_rule)

    def flow_capacity_upper(m, s, i, j, c):
        line = line_by_key[(i, j)]
        z = circuit_status(m, s, i, j, c)
        return m.flow[s, i, j, c] <= float(line["capacity_mw"]) * z
    def flow_capacity_lower(m, s, i, j, c):
        line = line_by_key[(i, j)]
        z = circuit_status(m, s, i, j, c)
        return m.flow[s, i, j, c] >= -float(line["capacity_mw"]) * z
    def dc_flow_upper(m, s, i, j, c):
        line = line_by_key[(i, j)]
        z = circuit_status(m, s, i, j, c)
        susceptance = base_mva / float(line["reactance_pu"])
        return m.flow[s, i, j, c] - susceptance * (m.theta[s, i] - m.theta[s, j]) <= big_m * (1 - z)
    def dc_flow_lower(m, s, i, j, c):
        line = line_by_key[(i, j)]
        z = circuit_status(m, s, i, j, c)
        susceptance = base_mva / float(line["reactance_pu"])
        return m.flow[s, i, j, c] - susceptance * (m.theta[s, i] - m.theta[s, j]) >= -big_m * (1 - z)

    def circuit_status(m, s, i, j, c):
        line = line_by_key[(i, j)]
        existing = int(line["existing_circuits"])
        outage = next(x for x in scenarios if x["name"] == s).get("line_outage")
        if c <= existing:
            if outage is not None and tuple(sorted((i, j))) == tuple(sorted(outage)):
                return 0
            return 1
        slot = c - existing
        return m.build[i, j, slot]

    m.flow_cap_upper = pyo.Constraint(m.S, m.LC, rule=flow_capacity_upper)
    m.flow_cap_lower = pyo.Constraint(m.S, m.LC, rule=flow_capacity_lower)
    m.dc_flow_upper = pyo.Constraint(m.S, m.LC, rule=dc_flow_upper)
    m.dc_flow_lower = pyo.Constraint(m.S, m.LC, rule=dc_flow_lower)

    m.reference_angle = pyo.Constraint(m.S, rule=lambda m, s: m.theta[s, int(case["slack_bus"])] == 0)

    def balance_rule(m, s, bus):
        gen = sum(
            m.generation[s, g["unit"], b]
            for g in generators if int(g["bus"]) == int(bus)
            for b in range(1, 4)
        )
        wind = sum(
            m.wind_generation[s, w["unit"]]
            for w in wind_units if int(w["bus"]) == int(bus)
        )
        shed = sum(m.shed[s, d["demand"]] for d in demands if int(d["bus"]) == int(bus))
        served = sum(
            m.consumption[s, d["demand"], b]
            for d in demands if int(d["bus"]) == int(bus)
            for b in range(1, 4)
        )
        outgoing = sum(m.flow[s, i, j, c] for i, j, c in circuit_keys if i == int(bus))
        incoming = sum(m.flow[s, i, j, c] for i, j, c in circuit_keys if j == int(bus))
        return gen + wind + shed + incoming - outgoing - served == 0
    m.balance = pyo.Constraint(m.S, m.N, rule=balance_rule)

    investment_cost_eur = sum(
        float(line_by_key[(i, j)]["investment_kEUR"]) * 1000 * m.build[i, j, slot]
        for i, j, slot in m.C
    )
    m.budget = pyo.Constraint(
        expr=investment_cost_eur <= float(p["investment_budget_kEUR"]) * 1000
    )

    def scenario_welfare(s):
        demand_value = sum(
            float(next(d for d in demands if d["demand"] == demand)[f"bid{block}_eur_mwh"])
            * m.consumption[s, demand, block]
            for demand, block in demand_keys
        )
        generation_cost = sum(
            float(next(g for g in generators if g["unit"] == unit)[f"offer{block}_eur_mwh"])
            * m.generation[s, unit, block]
            for unit, block in gen_keys
        )
        wind_cost = sum(
            float(next(w for w in wind_units if w["unit"] == unit).get("offer_price_mwh", 0.0))
            * m.wind_generation[s, unit]
            for unit in wind_keys
        )
        shed_cost = sum(
            load_shedding_multiplier * float(next(d for d in demands if d["demand"] == demand)["bid1_eur_mwh"])
            * m.shed[s, demand]
            for demand in [d["demand"] for d in demands]
        )
        return demand_value - generation_cost - wind_cost - shed_cost

    m.welfare = pyo.Expression(m.S, rule=lambda m, s: scenario_welfare(s))
    weighted_welfare = sigma * sum(float(s["weight"]) * m.welfare[s["name"]] for s in scenarios)
    annualized_investment = crf * investment_cost_eur
    if objective_mode == "aligned_welfare":
        m.objective = pyo.Objective(expr=weighted_welfare - annualized_investment, sense=pyo.maximize)
    elif objective_mode == "classic_min_cost":
        # Garces' alternative upper objective (20): total investment plus
        # annualized load-shedding cost, with one demand scenario at a time.
        annual_shed_cost = sigma * sum(
            load_shedding_multiplier * float(next(d for d in demands if d["demand"] == demand)["bid1_eur_mwh"])
            * m.shed[s["name"], demand]
            for s in scenarios
            for demand in [d["demand"] for d in demands]
        )
        m.objective = pyo.Objective(expr=investment_cost_eur + annual_shed_cost, sense=pyo.minimize)
    else:
        raise ValueError(f"Unknown objective_mode: {objective_mode}")
    m._scenario_weights = {s["name"]: float(s["weight"]) for s in scenarios}
    m._investment_cost_eur = investment_cost_eur
    m._crf = crf
    m._line_by_key = line_by_key
    m._candidate_keys = candidate_keys
    return m


def solve_integrated(
    case: dict,
    *,
    reported_crf: bool = True,
    objective_mode: str = "aligned_welfare",
    time_limit_s: int | None = None,
):
    model = build_integrated_model(case, reported_crf=reported_crf, objective_mode=objective_mode)
    solver = pyo.SolverFactory("appsi_highs")
    if time_limit_s is not None:
        solver.options["time_limit"] = time_limit_s
    results = solver.solve(model, tee=False)
    if results.solver.termination_condition not in {
        pyo.TerminationCondition.optimal,
        pyo.TerminationCondition.feasible,
    }:
        raise RuntimeError(f"HiGHS termination: {results.solver.termination_condition}")
    plan = []
    for (i, j), slot in model._candidate_keys:
        if pyo.value(model.build[i, j, slot]) > 0.5:
            plan.append({"from_bus": i, "to_bus": j, "slot": slot})
    return {
        "termination": str(results.solver.termination_condition),
        "objective_eur": pyo.value(model.objective),
        "investment_eur": pyo.value(model._investment_cost_eur),
        "investment_MEUR": pyo.value(model._investment_cost_eur) / 1e6,
        "crf": model._crf,
        "plan": plan,
        "scenario_social_welfare_MEUR_per_hour": {
            s: pyo.value(model.welfare[s]) / 1e6 for s in model.S
        },
        "expected_social_welfare_MEUR_per_year": sum(
            model._scenario_weights[s] * pyo.value(model.welfare[s]) * 8760 / 1e6
            for s in model.S
        ),
        "solver": "HiGHS via Pyomo appsi_highs",
        "objective_mode": objective_mode,
    }


def solve_market_for_fixed_plan(case: dict, plan: list[dict]):
    """Clear all Garces market scenarios for a fixed investment plan."""
    model = build_integrated_model(case, reported_crf=True, objective_mode="aligned_welfare")
    generators = case["generators"]
    wind_units = case.get("wind_units", [])
    demands = case["demands"]
    gen_keys = [(g["unit"], block) for g in generators for block in range(1, 4)]
    wind_keys = [w["unit"] for w in wind_units]
    demand_keys = [(d["demand"], block) for d in demands for block in range(1, 4)]
    selected = {(int(x["from_bus"]), int(x["to_bus"]), int(x["slot"])) for x in plan}
    for i, j, slot in model.C:
        model.build[i, j, slot].fix(1 if (i, j, slot) in selected else 0)
    solver = pyo.SolverFactory("appsi_highs")
    results = solver.solve(model, tee=False)
    if results.solver.termination_condition != pyo.TerminationCondition.optimal:
        raise RuntimeError(f"Fixed-plan market clearing termination: {results.solver.termination_condition}")
    welfare_currency = case.get("welfare_currency", "EUR")
    welfare_key = f"scenario_social_welfare_M{welfare_currency}_per_year"
    line_by_key = model._line_by_key
    circuit_loading = {}
    for s in model.S:
        rows = []
        for i, j, c in model.LC:
            line = line_by_key[(i, j)]
            flow = pyo.value(model.flow[s, i, j, c])
            capacity = float(line["capacity_mw"])
            if abs(flow) > 1e-7:
                rows.append({
                    "from_bus": int(i), "to_bus": int(j), "circuit": int(c),
                    "flow_mw": flow,
                    "capacity_mw": capacity,
                    "loading_percent": 100 * abs(flow) / capacity,
                })
        circuit_loading[s] = sorted(rows, key=lambda x: x["loading_percent"], reverse=True)
    return {
        welfare_key: {
            s: pyo.value(model.welfare[s]) * 8760 / 1e6 for s in model.S
        },
        "scenario_load_shed_mw": {
            s: sum(pyo.value(model.shed[s, d["demand"]]) for d in case["demands"])
            for s in model.S
        },
        "scenario_load_shed_by_demand_mw": {
            s: {
                d["demand"]: pyo.value(model.shed[s, d["demand"]])
                for d in case["demands"]
                if pyo.value(model.shed[s, d["demand"]]) > 1e-7
            }
            for s in model.S
        },
        "scenario_thermal_generation_mw": {
            s: sum(pyo.value(model.generation[s, unit, block]) for unit, block in gen_keys)
            for s in model.S
        },
        "scenario_wind_generation_mw": {
            s: sum(pyo.value(model.wind_generation[s, unit]) for unit in wind_keys)
            for s in model.S
        },
        "scenario_consumption_mw": {
            s: sum(pyo.value(model.consumption[s, demand, block]) for demand, block in demand_keys)
            for s in model.S
        },
        "scenario_circuit_loading": circuit_loading,
        f"expected_social_welfare_M{welfare_currency}_per_year": sum(
            model._scenario_weights[s] * pyo.value(model.welfare[s]) * 8760 / 1e6
            for s in model.S
        ),
    }
