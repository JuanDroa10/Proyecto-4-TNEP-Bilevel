"""Diagnostic: upper level scores gross welfare, while market keeps net W."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.rts24 import load_rts24
from tnep.models.primal_dual import solve_primal_dual


def main() -> None:
    case = load_rts24("multicontingency", load_shedding_multiplier=100)
    started = time.perf_counter()
    result = solve_primal_dual(
        case,
        upper_objective_mode="gross_welfare",
        time_limit_s=900,
    )
    result["wall_time_s"] = time.perf_counter() - started
    result["diagnostic_note"] = (
        "Market followers retain the 100x shedding penalty; only the upper-level "
        "reported welfare omits that penalty. This is diagnostic and is not the "
        "baseline formulation stated in Garces."
    )
    output = Path("results/garces_validation/rts24_multicontingency_gross_upper_diagnostic.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
