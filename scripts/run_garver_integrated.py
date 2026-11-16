"""Solve the preliminary Garver integrated-primal reference model."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tnep.data.garver import load_garver
from tnep.models.integrated_primal import solve_integrated


def main() -> None:
    start = time.perf_counter()
    result = solve_integrated(load_garver(), reported_crf=True)
    result["wall_time_s"] = time.perf_counter() - start
    output = Path("results/garces_validation/garver_integrated_primal.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
