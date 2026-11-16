"""Explicit primal-dual/strong-duality MILP for aligned Garces objectives.

The operation subproblem is a continuous LP conditional on the binary network
plan. Since scenarios are independent and have strictly positive weights, the
weighted sum of their market objectives has exactly the same maximizers as
solving every market scenario separately. Pyomo's LP dualizer generates the
explicit dual; the only resulting nonlinearities are binary build x dual
products in the dual objective. They are linearized with McCormick envelopes
and the documented Gamma bound.
"""
from __future__ import annotations

import pyomo.environ as pyo
from pyomo.repn.standard_repn import generate_standard_repn

from tnep.models.integrated_primal import build_integrated_model


FOLLOWER_COMPONENTS = (
    "gen_cap", "wind_cap", "demand_cap", "min_demand", "shed_cap",
    "flow_cap_upper", "flow_cap_lower", "dc_flow_upper", "dc_flow_lower",
    "reference_angle", "balance",
)


def _linearize_dual_objective(model: pyo.ConcreteModel, gamma: float):
    dual_obj = model.dual_market.obj.expr
    repn = generate_standard_repn(dual_obj, compute_values=True, quadratic=True)
    if repn.nonlinear_expr is not None:
        raise ValueError("Dual objective contains unsupported nonlinear terms")

    build_ids = {id(v): v for v in model.build.values()}
    products = []
    for pair in repn.quadratic_vars:
        a, b = pair
        if (id(a) in build_ids) == (id(b) in build_ids):
            raise ValueError(
                "Expected each quadratic dual-objective term to contain exactly "
                f"one investment binary; got {a.name} * {b.name}"
            )
        z, lam = (a, b) if id(a) in build_ids else (b, a)
        if lam.lb is not None and float(lam.lb) < -1e-9:
            raise ValueError(f"Dual variable {lam.name} is not nonnegative")
        products.append((z, lam))

    model.dual_product = pyo.Var(range(len(products)), domain=pyo.NonNegativeReals)
    model.dual_product_linearization = pyo.ConstraintList()
    for k, (z, lam) in enumerate(products):
        model.dual_product[k].setub(gamma)
        model.dual_product_linearization.add(model.dual_product[k] <= gamma * z)
        model.dual_product_linearization.add(model.dual_product[k] <= lam)
        model.dual_product_linearization.add(
            model.dual_product[k] >= lam - gamma * (1 - z)
        )

    linearized_expr = repn.constant or 0.0
    for variable, coefficient in zip(repn.linear_vars, repn.linear_coefs):
        linearized_expr += coefficient * variable
    for k, coefficient in enumerate(repn.quadratic_coefs):
        linearized_expr += coefficient * model.dual_product[k]
    model.dual_market.obj.deactivate()
    model.dual_objective_expression = pyo.Expression(expr=linearized_expr)
    model.strong_duality = pyo.Constraint(
        expr=sum(float(s["weight"]) * model.welfare[s["name"]]
                 for s in model._scenario_data)
        == model.dual_objective_expression
    )
    return len(products)


def build_primal_dual_model(
    case: dict,
    *,
    reported_crf: bool = True,
    gamma_max: float | None = None,
    upper_objective_mode: str = "aligned_welfare",
) -> pyo.ConcreteModel:
    """Build the upper-level model plus primal, dual and strong duality."""
    model = build_integrated_model(case, reported_crf=reported_crf)
    gamma = float(gamma_max or case["parameters"].get("gamma_max_dual", 1000))
    model._scenario_data = case["scenarios"]

    if upper_objective_mode not in {"aligned_welfare", "gross_welfare"}:
        raise ValueError("upper_objective_mode must be aligned_welfare or gross_welfare")
    # Gross welfare excludes the load-shedding penalty. Keep it available as
    # a diagnostic metric; followers always maximize the stated net welfare.
    demands = case["demands"]
    shed_multiplier = float(case["parameters"].get("load_shedding_penalty_multiplier", 100))
    model.gross_welfare = pyo.Expression(
        model.S,
        rule=lambda m, s: m.welfare[s] + sum(
            shed_multiplier * float(next(d for d in demands if d["demand"] == demand)["bid1_eur_mwh"])
            * m.shed[s, demand]
            for demand in [d["demand"] for d in demands]
        ),
    )

    # Create the market LP on the already declared primal variables. The
    # investment binaries are parameters from the follower's point of view.
    follower = pyo.ConcreteModel(name="combined_market_primal")
    follower.constraints = pyo.ConstraintList()
    for component_name in FOLLOWER_COMPONENTS:
        component = getattr(model, component_name)
        for row in component.values():
            follower.constraints.add(row.expr)
    follower.objective = pyo.Objective(
        expr=sum(float(s["weight"]) * model.welfare[s["name"]]
                 for s in case["scenarios"]),
        sense=pyo.maximize,
    )

    dual = pyo.TransformationFactory("core.lp_dual").create_using(
        follower, parameterize_wrt=list(model.build.values())
    )
    # Retain an explicit dual block in the final MILP and cap dual variables
    # at Gamma_max, as in the paper's disjunctive product linearization.
    model.dual_market = pyo.Block(concrete=True)
    model.dual_market.transfer_attributes_from(dual)
    for variable in model.dual_market.x.values():
        variable.setub(gamma)

    n_products = _linearize_dual_objective(model, gamma)
    if upper_objective_mode == "gross_welfare":
        sigma = float(case["parameters"]["annual_hours_sigma"])
        model.del_component(model.objective)
        model.objective = pyo.Objective(
            expr=sigma * sum(
                float(s["weight"]) * model.gross_welfare[s["name"]]
                for s in case["scenarios"]
            ) - model._crf * model._investment_cost_eur,
            sense=pyo.maximize,
        )
    model._gamma_max = gamma
    model._dual_product_count = n_products
    model._upper_objective_mode = upper_objective_mode
    model._primal_dual_formulation = "Pyomo core.lp_dual + strong duality + McCormick"
    return model


def solve_primal_dual(
    case: dict,
    *,
    reported_crf: bool = True,
    gamma_max: float | None = None,
    upper_objective_mode: str = "aligned_welfare",
    time_limit_s: int | None = None,
    tee: bool = False,
) -> dict:
    model = build_primal_dual_model(
        case, reported_crf=reported_crf, gamma_max=gamma_max,
        upper_objective_mode=upper_objective_mode,
    )
    solver = pyo.SolverFactory("appsi_highs")
    if time_limit_s is not None:
        solver.options["time_limit"] = time_limit_s
    results = solver.solve(model, tee=tee)
    if results.solver.termination_condition != pyo.TerminationCondition.optimal:
        raise RuntimeError(f"HiGHS termination: {results.solver.termination_condition}")

    plan = []
    for i, j, slot in model.C:
        if pyo.value(model.build[i, j, slot]) > 0.5:
            plan.append({"from_bus": int(i), "to_bus": int(j), "slot": int(slot)})
    expected = sum(
        float(s["weight"]) * pyo.value(model.welfare[s["name"]]) * 8760 / 1e6
        for s in case["scenarios"]
    )
    expected_gross = sum(
        float(s["weight"]) * pyo.value(
            model.gross_welfare[s["name"]] if hasattr(model, "gross_welfare")
            else model.welfare[s["name"]]
        ) * 8760 / 1e6
        for s in case["scenarios"]
    )
    dual_values = [pyo.value(v) for v in model.dual_market.x.values()]
    dual_saturation_count = sum(v >= model._gamma_max - 1e-6 for v in dual_values)
    return {
        "termination": str(results.solver.termination_condition),
        "objective_eur": pyo.value(model.objective),
        "investment_eur": pyo.value(model._investment_cost_eur),
        "investment_MEUR": pyo.value(model._investment_cost_eur) / 1e6,
        "crf": model._crf,
        "plan": plan,
        "scenario_social_welfare_MEUR_per_hour": {
            s["name"]: pyo.value(model.welfare[s["name"]]) / 1e6
            for s in case["scenarios"]
        },
        "expected_social_welfare_MEUR_per_year": expected,
        "expected_gross_social_welfare_MEUR_per_year": expected_gross,
        "solver": "HiGHS via Pyomo appsi_highs",
        "formulation": model._primal_dual_formulation,
        "upper_objective_mode": model._upper_objective_mode,
        "gamma_max_dual": model._gamma_max,
        "max_dual_value": max(dual_values, default=0.0),
        "dual_values_at_gamma_max": dual_saturation_count,
        "linearized_binary_dual_products": model._dual_product_count,
        "strong_duality_residual_eur_per_hour": (
            sum(float(s["weight"]) * pyo.value(model.welfare[s["name"]])
                for s in case["scenarios"])
            - pyo.value(model.dual_objective_expression)
        ),
    }
