"""Solve Garver with explicit market primal/dual and strong duality."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.garver import load_garver
from tnep.models.primal_dual import solve_primal_dual


def main() -> None:
    start = time.perf_counter()
    case = load_garver()
    result = solve_primal_dual(case)
    result["wall_time_s"] = time.perf_counter() - start
    output = Path("results/garces_validation/garver_primal_dual.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
