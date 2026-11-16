"""Sensitivity: RTS-24 22-scenario model with 10x load-shedding penalty."""
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
    case = load_rts24("multicontingency", load_shedding_multiplier=10)
    result = solve_integrated(case, reported_crf=True, time_limit_s=1800)
    result["load_shedding_penalty_multiplier_sensitivity"] = 10
    result["wall_time_s"] = time.perf_counter() - start
    output = Path("results/garces_validation/rts24_multicontingency_ls10_sensitivity.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
