# Registro de correcciones de la entrega

Fecha: 15 de noviembre de 2026 (America/Bogota). Se conserva intacto el ZIP original; esta carpeta es una versión corregida.

## Cambios comprobados

1. Se revisó visualmente la Tabla 4 de Heydari (PDF, p. 9) y se corrigieron los cuatro planes HVAC del CSV de referencia. `heydari.py` ya no mantiene una segunda copia codificada de los planes: los carga y valida directamente desde el CSV.
2. Se incorporó `fixed_plan_scipy.py`, un despeje LP independiente para planes fijos. Su implementación se cotejó con resultados Pyomo previamente guardados usando los planes originales: reprodujo 463.58581 MUSD/año (caso 1) y 439.25203 MUSD/año (caso 2, duración). Luego se recalcularon los JSON de Heydari con los planes correctos y se repitió la sensibilidad ±0.01 p.u.
3. Se añadió `evaluate_uncertainty_plans.py` para valorar duración, PEM y Monte Carlo bajo los mismos cinco estados de carga. El valor del plan de duración obtenido por este LP coincide con el óptimo MILP guardado a mejor que 1e-5 M€/año. La evaluación revela 15.176 MW no servidos en el estado de 0.914 p.u. para el plan de Monte Carlo reducido.
4. Se actualizó el análisis en `README.md`, `reports/heydari_validation.md`, `reports/uncertainty_methods.md`, `reports/formulation_implementation.md` y `reports/source_audit.md`. Se quitó la nota obsoleta de Garver que decía que aún faltaba implementar el dual. Se corrigió un dato de referencia de Garver Tabla V (fila de salida 2–3).
5. Se renovó `results/logs/run_manifest.csv` tras generar los resultados.

## Estado de reproducibilidad y límites

- Las nuevas verificaciones con planes fijos se ejecutaron con SciPy/HiGHS; el entorno de esta corrección no disponía de Pyomo/HiGHS Python, por lo que **no se volvieron a resolver los MILP originales**. Sus resultados originales permanecen en el ZIP y se distinguen de los nuevos por sus scripts y metadatos.
- La verificación de Heydari es a plan fijo y con datos reconstruidos; no prueba que el plan publicado sea óptimo. La ponderación de 30 estados iguales discrepa de la Tabla 4. No se reconstruyeron HVDC, costos de inversión USD ni CVaR.
- RTS-24 multi-contingencia continúa con plan y bienestar discrepantes. Garver Tabla V sólo tiene la referencia corregida; no tiene una ejecución de validación de contingencias.
- Monte Carlo reducido conserva sus tres escenarios y el resultado original para que sea posible auditar la falla. El nuevo informe compara su plan sobre una referencia común y recomienda una reducción que preserve el pico, sin presentar esta recomendación como una nueva optimización ya realizada.

## Orden recomendado de ejecución

```text
python scripts/build_heydari_fig2_scenarios.py
python scripts/run_heydari_reconstructed_market.py
python scripts/bound_heydari_digitization_error.py
python scripts/evaluate_uncertainty_plans.py
python scripts/build_run_manifest.py
```

La reoptimización original de Garcés y los tres métodos requiere el entorno Pyomo/HiGHS descrito en `README.md`. Si se corre `compare_uncertainty_methods.py`, este actualiza automáticamente la evaluación común.
