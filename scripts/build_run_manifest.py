"""Write hashes and solver metadata for the structured result artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUT = RESULTS / "logs" / "run_manifest.csv"


def find_values(obj, key):
    found = []
    if isinstance(obj, dict):
        if key in obj:
            found.append(obj[key])
        for value in obj.values():
            found.extend(find_values(value, key))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(find_values(value, key))
    return found


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(RESULTS.rglob("*.json")):
        if path == RESULTS / "logs" / "run_manifest.json":
            continue
        raw = path.read_bytes()
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = {}
        solvers = sorted({str(x) for x in find_values(data, "solver")})
        terminations = sorted({str(x) for x in find_values(data, "termination")})
        wall_times = [float(x) for x in find_values(data, "wall_time_s") if isinstance(x, (int, float))]
        rows.append({
            "artifact": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "solver": ";".join(solvers),
            "termination": ";".join(terminations),
            "recorded_wall_time_s": ";".join(f"{x:.6f}" for x in wall_times),
        })
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {OUTPUT} ({len(rows)} result artifacts)")


if __name__ == "__main__":
    main()
