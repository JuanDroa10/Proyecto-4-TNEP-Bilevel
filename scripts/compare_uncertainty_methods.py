"""Compare load-duration, Hong 2n+1 PEM and reduced Monte Carlo for Garver.

This is a controlled demand-uncertainty extension: it uses Garces' Garver
network, EUR bids/offers and EUR investment costs, and the five load factors
digitized from Heydari Fig. 2. Wind is held out so no missing wind/network or
currency assumptions enter the expansion objective.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import root

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.garver import load_garver
from tnep.models.integrated_primal import solve_integrated


ROOT = Path(__file__).resolve().parents[1]
LOAD_CSV = ROOT / "data/uncertainty/heydari_fig2_load_points.csv"
N_MC = 100_000
MC_SEED = 20261106
REDUCED_SCENARIOS = 3


def _scenario(name: str, factor: float, weight: float) -> dict:
    return {
        "name": name,
        "weight": float(weight),
        "demand_factors": {bus: float(factor) for bus in range(1, 7)},
        "wind_availability": {},
        "line_outage": None,
    }


def hong_2n1_points(values: np.ndarray, probabilities: np.ndarray) -> list[dict]:
    """Three points, central point at mean, matching moments 1--4 (n=1)."""
    mean = float(np.dot(values, probabilities))
    centered = values - mean
    moments = np.array([
        np.dot(probabilities, centered ** k) for k in range(1, 5)
    ])

    def residual(q):
        lower_dev, upper_dev, lower_w, upper_w = q
        return np.array([
            lower_w * lower_dev + upper_w * upper_dev - moments[0],
            lower_w * lower_dev**2 + upper_w * upper_dev**2 - moments[1],
            lower_w * lower_dev**3 + upper_w * upper_dev**3 - moments[2],
            lower_w * lower_dev**4 + upper_w * upper_dev**4 - moments[3],
        ])

    result = root(residual, [-0.29, 0.21, 0.17, 0.23])
    if not result.success or np.max(np.abs(residual(result.x))) > 1e-8:
        raise RuntimeError(f"Hong 2n+1 moment fit failed: {result.message}")
    lower_dev, upper_dev, lower_w, upper_w = map(float, result.x)
    center_w = 1.0 - lower_w - upper_w
    points = [
        {"scenario_id": "PEM_L", "load_factor_pu": mean + lower_dev, "weight": lower_w},
        {"scenario_id": "PEM_M", "load_factor_pu": mean, "weight": center_w},
        {"scenario_id": "PEM_H", "load_factor_pu": mean + upper_dev, "weight": upper_w},
    ]
    if min(x["weight"] for x in points) < 0 or not np.isclose(sum(x["weight"] for x in points), 1):
        raise ValueError("Hong 2n+1 fit has invalid weights")
    if not all(values.min() - 1e-10 <= x["load_factor_pu"] <= values.max() + 1e-10 for x in points):
        raise ValueError("Hong 2n+1 point lies outside observed load-factor support")
    return points


def _cluster_cost(values: np.ndarray, weights: np.ndarray, i: int, j: int):
    w = weights[i:j]
    x = values[i:j]
    mu = float(np.dot(w, x) / w.sum())
    return float(np.dot(w, (x - mu) ** 2)), mu, float(w.sum())


def reduce_1d_weighted(values: np.ndarray, weights: np.ndarray, k: int) -> list[dict]:
    """Optimal contiguous weighted 1-D k-means by dynamic programming."""
    order = np.argsort(values)
    x = np.asarray(values, dtype=float)[order]
    w = np.asarray(weights, dtype=float)[order]
    n = len(x)
    if not 1 <= k <= n:
        raise ValueError("Invalid cluster count")
    dp = np.full((k + 1, n + 1), np.inf)
    previous = np.full((k + 1, n + 1), -1, dtype=int)
    dp[0, 0] = 0.0
    for groups in range(1, k + 1):
        for end in range(groups, n + 1):
            for start in range(groups - 1, end):
                cost = _cluster_cost(x, w, start, end)[0]
                candidate = dp[groups - 1, start] + cost
                if candidate < dp[groups, end]:
                    dp[groups, end] = candidate
                    previous[groups, end] = start
    clusters = []
    end = n
    for groups in range(k, 0, -1):
        start = int(previous[groups, end])
        cost, mean, weight = _cluster_cost(x, w, start, end)
        clusters.append({
            "scenario_id": f"MC_R{groups}", "load_factor_pu": mean,
            "weight": weight / float(np.sum(w)), "members": end - start,
            "weighted_squared_error": cost,
        })
        end = start
    return list(reversed(clusters))


def run_method(case_base: dict, method: str, points: list[dict], input_meta: dict) -> dict:
    case = dict(case_base)
    case["scenarios"] = [
        _scenario(point["scenario_id"], point["load_factor_pu"], point["weight"])
        for point in points
    ]
    started = time.perf_counter()
    result = solve_integrated(case, reported_crf=True)
    result["wall_time_s"] = time.perf_counter() - started
    return {
        "method": method,
        "points": points,
        "input": input_meta,
        "optimization": result,
    }


def main() -> None:
    load = pd.read_csv(LOAD_CSV)
    load_values = load["load_factor_pu"].to_numpy(dtype=float)
    duration_prob = load["duration_hours"].to_numpy(dtype=float) / 8760.0
    if not np.isclose(duration_prob.sum(), 1.0):
        raise ValueError("Load-duration weights must sum to one")

    duration_points = [
        {"scenario_id": f"L{int(row.load_block)}", "load_factor_pu": float(row.load_factor_pu),
         "weight": float(row.duration_hours) / 8760.0}
        for row in load.itertuples()
    ]
    pem_points = hong_2n1_points(load_values, duration_prob)

    rng = np.random.default_rng(MC_SEED)
    samples = rng.choice(load_values, size=N_MC, p=duration_prob)
    mc_values, counts = np.unique(samples, return_counts=True)
    mc_weights = counts.astype(float) / N_MC
    reduced_points = reduce_1d_weighted(mc_values, mc_weights, REDUCED_SCENARIOS)
    true_load_mean = float(np.dot(load_values, duration_prob))
    sample_load_mean = float(np.mean(samples))
    sample_load_se = float(np.std(samples, ddof=1) / np.sqrt(N_MC))

    pd.DataFrame(duration_points).assign(method="duration_curve").to_csv(
        ROOT / "data/uncertainty/scenarios_duration_curve.csv", index=False
    )
    pd.DataFrame(pem_points).assign(method="hong_2n1_pem").to_csv(
        ROOT / "data/uncertainty/scenarios_hong_pem.csv", index=False
    )
    pd.DataFrame(reduced_points).assign(method="monte_carlo_reduced").to_csv(
        ROOT / "data/uncertainty/scenarios_monte_carlo_reduced.csv", index=False
    )

    base = load_garver()
    methods = [
        run_method(base, "duration_curve_5_segments", duration_points,
                   {"source": "manual digitization of Heydari Fig. 2 load curve", "n_scenarios": 5}),
        run_method(base, "hong_2n1_pem", pem_points,
                   {"random_variables": 1, "moments_matched": [1, 2, 3, 4], "n_scenarios": 3}),
        run_method(base, "monte_carlo_then_reduction", reduced_points,
                   {"seed": MC_SEED, "draws": N_MC, "unique_draws": int(len(mc_values)),
                    "reduced_scenarios": REDUCED_SCENARIOS, "reduction": "optimal weighted 1-D k-means",
                    "exact_duration_mean_load_factor": true_load_mean,
                    "monte_carlo_sample_mean_load_factor": sample_load_mean,
                    "monte_carlo_mean_standard_error": sample_load_se}),
    ]
    output = ROOT / "results/uncertainty/garver_demand_method_comparison.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(methods, indent=2), encoding="utf-8")
    # Recompute plan quality on one common reference distribution after every
    # optimization run; method-specific objective values are not comparable.
    from evaluate_uncertainty_plans import evaluate_all
    evaluate_all()
    print(json.dumps(methods, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
