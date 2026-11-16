"""Write a small, reproducible inventory of the Python optimization stack."""
from __future__ import annotations

import platform
from pathlib import Path

import highspy
import numpy
import pandas
import pyomo
import scipy
from pyomo.contrib.appsi.solvers import Highs


def main() -> None:
    available = Highs().available()
    lines = [
        f"Python: {platform.python_version()}",
        f"Platform: {platform.platform()}",
        f"NumPy: {numpy.__version__}",
        f"pandas: {pandas.__version__}",
        f"SciPy: {scipy.__version__}",
        f"Pyomo: {pyomo.__version__}",
        f"HiGHS: {highspy.Highs().version()}",
        f"Pyomo appsi_highs availability: {available}",
    ]
    output = Path("results/logs/environment.txt")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
