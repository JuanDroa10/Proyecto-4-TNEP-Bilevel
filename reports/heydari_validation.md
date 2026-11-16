# Verificación parcial de Heydari y Barforoushi (2024): Garver

## Alcance y corrección de la Tabla 4

El artículo no aporta la hoja original de red ni las coordenadas numéricas de la Figura 2; declara que los datos están disponibles bajo solicitud. Se reconstruyeron líneas HVAC con la Tabla I de Garcés (2009), precios con la Tabla 3 de Heydari y perfiles con digitalización manual de la Figura 2. Por ello las cifras son una **verificación aproximada del mercado con plan fijo**, no la reproducción de la optimización de inversión de Heydari.

La primera transcripción del plan de la Tabla 4 desplazó líneas entre columnas. Se cotejó visualmente el PDF (página 9) y se corrigió `data/uncertainty/heydari_garver_reference_results.csv`. Los planes comparables son:

| Caso | Adiciones HVAC publicadas | Circuitos nuevos |
|---|---|---:|
| 1 | 2–6 (4); 3–5 (3) | 7 |
| 2 | 2–6 (4); 3–5 (2); 4–6 (2); 5–6 (2) | 10 |

`src/tnep/data/heydari.py` lee ahora los planes directamente del CSV y valida los circuitos. El caso 3 incorpora además 3–6 (1) y HVDC 2–6 (1); el caso 4 tiene 4–6 (3) y HVDC 2–6 (1). Los casos 3–4 no se simularon por falta de parámetros originales HVDC.

## Bienestar social con el plan fijo

`run_heydari_reconstructed_market.py` despeja los escenarios con `fixed_plan_scipy.py` (SciPy/HiGHS), LP independiente de Pyomo con los límites, balances, flujos DC y bienestar de la reconstrucción. Antes de corregir los planes, este LP reprodujo los valores registrados anteriormente (463.58581 y 439.25203 MUSD/año). Después de la corrección:

| Caso / ponderación | Tabla 4 (MUSD/año) | Reconstrucción (MUSD/año) | Error |
|---|---:|---:|---:|
| 1, horas de cinco bloques de carga | 462.64 | 462.34463 | −0.064 % |
| 2, horas de bloque × 1/6 por estado eólico | 527.62 | 528.88177 | +0.239 % |
| 2, 30 estados con igual peso | 527.62 | 452.19717 | −14.295 % |

La cercanía de los dos primeros valores es indicio de coherencia bajo ponderación por duración; **no prueba identidad de datos ni optimalidad del plan**. La formulación del artículo usa horas por bloque `N_t` y pesos eólicos `δ(ω)`, pero su descripción del caso Garver también dice que todos los escenarios pesan igual. Se conservan ambas lecturas sin atribuir a los autores la que mejor ajusta.

Como comprobación secundaria, las energías anuales bajo ponderación por duración son (GWh/año):

| Caso y métrica | Publicado | Reconstruido |
|---|---:|---:|
| 1, generación fósil / consumo | 9627.92 / 9627.92 | 9621.23 / 9621.23 |
| 2, generación fósil | 7120.48 | 7038.07 |
| 2, generación eólica | 2213.81 | 2228.88 |
| 2, consumo | 9400.21 | 9332.59 |

El caso 2 reconstruido presenta carga no servida en estados de carga alta (máximo 194.89 MW). Los valores por escenario están en `results/heydari_validation/heydari_garver_reconstructed_market.json`.

## Sensibilidad de la lectura de la Figura 2

Se desplazaron todos los factores de carga y/o viento ±0.01 p.u., manteniendo el **plan corregido** del caso 2 y los pesos por duración. Son perturbaciones comunes de los puntos, no una cota matemática para cualquier combinación independiente de errores.

| Perturbación | Bienestar (MUSD/año) |
|---|---:|
| Nominal | 528.88177 |
| Carga −0.01 | 533.79940 |
| Carga +0.01 | 519.61936 |
| Viento −0.01 | 515.48811 |
| Viento +0.01 | 542.01192 |
| Carga −0.01 y viento +0.01 | 546.83570 |
| Carga +0.01 y viento −0.01 | 500.53336 |

Ahora 527.62 MUSD/año **sí queda dentro del intervalo explorado**. La diferencia nominal no se puede atribuir exclusivamente a digitalización porque también son inciertos los datos de red y los pesos. Resultados: `results/heydari_validation/heydari_fig2_digitization_sensitivity.json`.

## Límites para una validación completa

- No se optimizaron las inversiones de Heydari; se fijaron sus planes publicados. Garcés informa costos en EUR y Heydari en USD. El campo `garces_cost_proxy_MEUR` del JSON es sólo una suma orientativa en EUR, nunca una comparación con la inversión de la Tabla 4.
- Faltan los datos exactos de red HVAC/HVDC de [41], costos en USD, perfiles y probabilidades. No se compararon formalmente costos, objetivo superior, LMP ni optimalidad de los planes.
- No se reconstruyó HVDC para casos 3–4 ni CVaR para el caso 4.
- Los puntos de Figura 2 son digitalización manual, no datos oficiales.

## Reproducción

Desde la raíz del proyecto con las dependencias de `requirements-lock.txt`:

```text
python scripts/build_heydari_fig2_scenarios.py
python scripts/run_heydari_reconstructed_market.py
python scripts/bound_heydari_digitization_error.py
```

Los dos últimos scripts requieren SciPy y no Pyomo. El CSV es la fuente de los planes; los JSON registran cada escenario y el solucionador utilizado.
