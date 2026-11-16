"""Solve RTS-24 without contingencies using explicit primal-dual MILP."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.rts24 import load_rts24
from tnep.models.primal_dual import solve_primal_dual


def main() -> None:
    started = time.perf_counter()
    case = load_rts24("no_contingencies")
    result = solve_primal_dual(case, time_limit_s=1800)
    result["wall_time_s"] = time.perf_counter() - started
    output = Path("results/garces_validation/rts24_no_contingencies_primal_dual.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
