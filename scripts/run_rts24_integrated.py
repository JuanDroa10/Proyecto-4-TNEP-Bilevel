"""Solve Garces RTS-24 without contingencies using the primal-integrated MILP."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.rts24 import load_rts24
from tnep.models.integrated_primal import solve_integrated


def main() -> None:
    start = time.perf_counter()
    result = solve_integrated(load_rts24(), reported_crf=True, time_limit_s=600)
    result["wall_time_s"] = time.perf_counter() - start
    output = Path("results/garces_validation/rts24_no_contingencies_integrated.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
