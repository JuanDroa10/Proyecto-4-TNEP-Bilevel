# Métodos de incertidumbre de demanda en Garver

## Alcance y tres métodos

Se conserva la red, ofertas, demandas y costos de inversión en EUR de Garcés. La incertidumbre es **un factor común de carga** digitalizado de la Figura 2 de Heydari. Se excluyó el viento de esta optimización para no combinar bienestar en USD de Heydari con inversiones en EUR de Garcés. Este experimento controlado **no reproduce** la expansión HVAC/HVDC de Heydari.

Los tres conjuntos se usan por separado para optimizar el mismo MILP primal integrado de Garcés (presupuesto 30 M€, CRF aproximado 0.10, penalización de carga no servida 100×):

1. **Curva de duración:** cinco factores 0.914, 0.773, 0.634, 0.479 y 0.334 p.u.; duran 1000, 3000, 3000, 1000 y 760 horas respectivamente.
2. **Hong PEM 2n+1 con n=1:** tres puntos (media y dos concentraciones) que igualan los primeros cuatro momentos de la distribución discreta. Sólo considera una variable aleatoria escalar; no modela carga y viento conjuntamente.
3. **Monte Carlo con reducción:** 100 000 extracciones de los cinco valores con semilla 20261106; k-means ponderado unidimensional reduce las observaciones a tres centros. Su criterio cuadrático no preserva necesariamente picos ni penalizaciones de carga no servida.

`compare_uncertainty_methods.py` reproduce las optimizaciones con Pyomo/HiGHS. `evaluate_uncertainty_plans.py` despeja los tres planes fijos sobre **los mismos cinco estados originales** con un LP independiente SciPy/HiGHS.

## Objetivos internos de cada método

| Método | Escenarios de optimización | Plan por corredor | Inversión (M€) | Objetivo con sus propios escenarios (M€/año) |
|---|---:|---|---:|---:|
| Duración | 5 | 2–6 (2); 3–5 | 15.4464 | 190.08570 |
| PEM | 3 | 2–6 (2); 3–5 | 15.4464 | 190.10598 |
| Monte Carlo reducido | 3 | 2–3; 2–6; 3–5 | 13.5156 | 190.09391 |

**Estos objetivos no miden de forma comparable la calidad de los planes:** cada uno promedia una distribución distinta. Los centros de Monte Carlo reducido son 0.4161, 0.6340 y 0.8077 p.u.; ninguno representa el pico original de 0.914 p.u.

## Evaluación común de los tres planes

Se fijó cada plan y se volvió a despejar el mercado para los cinco factores originales, ponderados por horas. Es una comparación bajo **una referencia común**, no una prueba fuera de la curva digitalizada.

| Plan obtenido con | Bienestar en cinco estados (M€/año) | Inversión anualizada (M€/año) | Objetivo neto común (M€/año) | Pérdida frente al óptimo de cinco estados (M€/año) |
|---|---:|---:|---:|---:|
| Duración | 191.63034 | 1.54464 | **190.08570** | 0 |
| PEM | 191.63034 | 1.54464 | **190.08570** | 0 |
| Monte Carlo reducido | 25.31976 | 1.35156 | **23.96820** | **166.11751** |

PEM construye el mismo número de circuitos por corredor que duración; puede elegir otro `slot` equivalente entre líneas paralelas. Ambos planes tienen el mismo desempeño al recuperar los cinco estados. El plan de Monte Carlo reducido **deja 15.176 MW de carga no servida en el estado 0.914 p.u., que dura 1000 horas**. La penalización de 100× explica casi toda su pérdida. Los otros cuatro niveles no presentan carga no servida con ese plan.

El error estándar muestral del factor medio (~0.00050 p.u.) no capta la reducción de escenarios ni el riesgo de una decisión discreta. Una sensibilidad futura debe conservar expresamente el pico o proteger la cola al reducir escenarios, y comparar después todos los planes bajo la misma referencia.

## Archivos y límites

- Escenarios: `data/uncertainty/scenarios_duration_curve.csv`, `scenarios_hong_pem.csv`, `scenarios_monte_carlo_reduced.csv`.
- Optimizaciones originales: `results/uncertainty/garver_demand_method_comparison.json`.
- Evaluación común y carga no servida por estado: `results/uncertainty/garver_common_evaluation.json`.
- Reproducción de evaluación común: `python scripts/evaluate_uncertainty_plans.py` (SciPy, sin Pyomo). Para volver a optimizar: `python scripts/compare_uncertainty_methods.py` (Pyomo/HiGHS; también actualiza la evaluación común).

La distribución procede de cinco puntos leídos de una figura; no hay datos meteorológicos horarios ni dependencia carga-viento. La evaluación común mide desempeño bajo esos cinco puntos, no garantiza desempeño real fuera de muestra. Los tiempos de solver dependen del entorno y no permiten una clasificación universal de métodos.
