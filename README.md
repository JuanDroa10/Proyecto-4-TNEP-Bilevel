# Proyecto 4: TNEP bi-nivel y análisis de incertidumbre

Implementación y auditoría del modelo de planificación de expansión de transmisión en mercado de Garcés et al. (IEEE, **2009**), reproducción de Garver y RTS-24, y comparación controlada de métodos de incertidumbre. La consigna menciona 2014, pero el artículo suministrado es de 2009.

## Estado actual

- Inventario inicial de los tres PDF disponibles: ver `reports/source_audit.md`.
- Las tablas Garver y RTS-24 se transcribieron desde el artículo y la tesis. El primal integrado y el primal-dual explícito reproducen Garver y RTS-24 sin contingencias dentro del 0.03% para inversión/beneficio medio; los residuos de dualidad fuerte son 0 y <1e-7 EUR/h, respectivamente.
- RTS-24 multi-contingencia está resuelto con HiGHS, pero no reproduce el plan/objetivo de Tabla X: con penalización 100× obtiene 29.31919 M€ y 518.76923 M€/año frente a 28.64 M€ y 717.97 M€/año. Para el plan publicado fijo, el bienestar neto modelado es 517.818 M€/año; al añadir de vuelta sólo para diagnóstico la penalización ponderada de carga no servida, la cifra es 717.451 M€/año (−0.072% de Tabla X). Esto sugiere una diferencia en la métrica reportada, pero contradice la definición de bienestar de las ecuaciones (1)/(5), que incluye esa penalización. El plan discrepante sigue sin explicación. Ver `reports/rts24_validation.md`.
- Se compararon curva de duración, Hong PEM 2n+1 y Monte Carlo reducido con incertidumbre de demanda de Garver y costos/precios EUR de Garcés. Al evaluar los tres planes sobre los mismos cinco estados, duración y PEM dan 190.08570 M€/año de objetivo neto, mientras el plan de Monte Carlo reducido da 23.96820 M€/año porque omite el pico. Viento se excluye del comparativo de expansión para no mezclar EUR y USD. Ver `reports/uncertainty_methods.md`.
- Corregida la transcripción de planes de Heydari, los despejes a plan fijo reconstruidos dan 462.34463 MUSD/año en caso 1 (−0.064% de Tabla 4) y 528.88177 MUSD/año en caso 2 con pesos por duración (+0.239%). Con 30 estados de igual peso, caso 2 da 452.19717 (−14.295%). No se optimizaron las inversiones ni se validaron los casos HVDC; ver `reports/heydari_validation.md`.
- Solver utilizado: HiGHS 1.15.1 mediante Pyomo 6.10.1 (`appsi_highs`).
- Los nuevos chequeos de planes fijos y evaluación común usan SciPy/HiGHS `linprog`; el solver exacto queda registrado en cada JSON.

## Instalación

Requiere Python 3.12 o posterior para instalar el conjunto fijado en `requirements-lock.txt`. Entorno validado: Python 3.14.7. En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

## Ejecución disponible

Desde la raíz del repositorio, con el entorno instalado:

```powershell
python scripts/run_garver_integrated.py
python scripts/run_garver_cost_min.py
python scripts/run_garver_primal_dual.py
python scripts/run_rts24_integrated.py
python scripts/run_rts24_cost_min.py
python scripts/run_rts24_primal_dual.py
python scripts/run_dual_gamma_sensitivity.py
python scripts/run_rts24_multicontingency.py
python scripts/run_rts24_multicontingency_ls10_sensitivity.py
python scripts/diagnose_rts24_published_multicontingency_plan.py
python scripts/analyze_rts24_table_x_welfare_accounting.py
python scripts/build_heydari_fig2_scenarios.py
python scripts/run_heydari_reconstructed_market.py
python scripts/bound_heydari_digitization_error.py
python scripts/compare_uncertainty_methods.py
python scripts/evaluate_uncertainty_plans.py
python scripts/build_run_manifest.py
```

Los JSON de `results/` guardan las ejecuciones originales de Garcés y las verificaciones corregidas de Heydari y de evaluación común. `scripts/check_environment.py` registra el solver y dependencias locales. RTS multi-contingencia sigue sin reproducir Tabla X. Heydari se verifica sólo con los planes publicados **fijos** y con datos reconstruidos; la interpretación de pesos uniformes no coincide con Tabla 4. Los dos scripts Heydari y `evaluate_uncertainty_plans.py` pueden ejecutarse con SciPy aun sin Pyomo.

## Reportes

- `../Informe_Proyecto_4_Ampliado.pdf`: informe ampliado de esta entrega; fuente editable en `../Overleaf_Proyecto_4/`.
- `reports/Informe_Proyecto_4.md`: versión previa en Markdown; la versión final editable está en `../Overleaf_Proyecto_4/`.
- `reports/formulation_implementation.md`: ecuaciones, equivalencia primal-dual, linealización y trazabilidad de datos.
- `reports/garces_validation.md`: Garver y comparación clásica.
- `reports/rts24_validation.md`: RTS-24 sin y con contingencias, incluido diagnóstico de Tabla X.
- `reports/uncertainty_methods.md`: comparación de curva de duración, PEM y Monte Carlo reducido.
- `reports/heydari_validation.md`: verificación parcial y sensibilidad de digitalización.
- `reports/correction_log.md`: cambios de esta revisión y archivos que aún no se han podido recalcular.

## Fuentes

Los PDF originales suministrados se conservan en la raíz del repositorio. `data/raw/source_manifest.csv` registra sus nombres y estado de revisión. No se altera el contenido de las fuentes.

