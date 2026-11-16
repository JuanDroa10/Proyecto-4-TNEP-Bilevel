# Validación preliminar de Garver (Garcés et al., 2009)

## Alcance

Se ejecutaron la formulación primal integrada equivalente y una formulación primal-dual explícita para Garver. La maximización del planificador usa el mismo beneficio social ponderado que maximizan los despejes de mercado, de modo que se pueden optimizar conjuntamente variables operativas y de inversión; el segundo modelo impone además dualidad fuerte para auditar la equivalencia.

Configuración: Pyomo 6.10.1, HiGHS 1.15.1, interfaz `appsi_highs`; factor de recuperación 0.10 para reproducir el artículo; 8760 horas/año; base de 100 MVA, inferida y corroborada por la concordancia numérica. El artículo utilizó GAMS/CPLEX 11.0 y reportó el factor de recuperación aproximadamente como 10%.

## Comparación con Tabla IV

| Métrica | Garcés publicado | Implementación actual | Error relativo |
|---|---:|---:|---:|
| Plan | 2-3 (1), 3-5 (1), 4-6 (3) | 2-3 (1), 3-5 (1), 4-6 (3) | Coincide |
| Inversión total (M€) | 25.10 | 25.1004 | 0.0016% |
| Beneficio social promedio (M€/año) | 292.71 | 292.7141 | 0.0014% |
| Tiempo de solver | 6.70 s | 0.49 s de pared | No comparable entre hardware/versiones |

Los errores de inversión y beneficio son menores que el redondeo de las cifras publicadas. El resultado de ejecución está guardado en `results/garces_validation/garver_integrated_primal.json`.

## Validación primal-dual explícita

Se implementó el dual LP del mercado con `core.lp_dual` de Pyomo, se impusieron factibilidad primal/dual y dualidad fuerte, y se linealizaron 468 productos binario-dual con McCormick y Γmax=1000.

| Métrica | MILP primal integrado | MILP primal-dual | Garcés publicado |
|---|---:|---:|---:|
| Plan por corredor | 2-3; 3-5; 4-6 (3) | Coincide | Coincide |
| Inversión (M€) | 25.1004 | 25.1004 | 25.10 |
| Bienestar medio (M€/año) | 292.7141 | 292.7141 | 292.71 |
| Residuo de dualidad fuerte | — | 0 EUR/h | — |

El resultado está en `results/garces_validation/garver_primal_dual.json`. Dieciocho variables duales alcanzan el bound Γ=1000 en una solución óptima degenerada; el certificado primal-dual mantiene residuo cero. El reporte conserva esta saturación para que se pueda revisar la sensibilidad de Γ.

Con Γ=2000 el plan por corredor y cantidad y el objetivo se mantienen iguales a Γ=1000 (diferencia menor que 1 EUR); 21 duales alcanzan el nuevo bound. Véase `results/garces_validation/dual_gamma_sensitivity.json`.

## Baseline clásica de minimización de costo

Se resolvió el problema para cada escenario por separado, minimizando inversión total más costo anualizado de carga no servida, y luego se despejó el mercado con cada plan fijo para calcular el beneficio social medio.

| Escenario | Plan publicado | Plan actual | Inversión publicada / actual (M€) | Beneficio medio publicado / actual (M€/año) |
|---|---|---|---:|---:|
| 1 | 3-5; 2-3; 2-6 (2) | Coincide | 19.31 / 19.3080 | -2613.02 / -2613.0261 |
| 2 | 3-5; 2-3; 4-6 (3) | Coincide | 25.10 / 25.1004 | 292.71 / 292.7141 |
| 3 | 3-5; 2-6; 4-6 (2) | Coincide | 21.24 / 21.2388 | -423.57 / -423.5745 |

Las inversiones y beneficios medios coinciden dentro del redondeo publicado. Los beneficios sociales correspondientes al escenario en la columna IV de la Tabla IV quedan pendientes de cotejo: el despeje de mercado del plan fijo produce 276.45, 307.79 y 303.19 M€/año para los escenarios 1, 2 y 3, frente a 275.60, 291.50 y 286.62 M€ publicados. Los valores promedio sí coinciden. Se conservará esta discrepancia en el reporte hasta determinar si proviene del significado/operación de esa columna, de datos originales no visibles o de una diferencia de formulación.

## Interpretación y límites

- La concordancia respalda la transcripción de las tablas Garver y el escalamiento de reactancia adoptado (100 MVA).
- La formulación primal-dual explícita coincide con el primal integrado en plan y objetivo. Algunos duales llegan al límite Γ incluso en la sensibilidad con Γ=2000; esto debe mantenerse visible y no interpretarse como una prueba general de que la cota nunca corta soluciones.
- La cifra de tiempo sólo describe este entorno; el artículo reporta GAMS/CPLEX 11.0 en Linux y hardware distinto.
- Se usó el factor de anualización aproximado de 0.10 informado para la reproducción. El CRF exacto a 10% y 25 años es 0.110168; se registrará como sensibilidad porque no es el valor aproximado que reproduce la tabla.

## Fuente

Garcés, L. P., Conejo, A. J., García-Bertrand, R., y Romero, R. (2009). “A Bilevel Approach to Transmission Expansion Planning Within a Market Environment.” *IEEE Transactions on Power Systems*, 24(3), 1513-1522. DOI: [10.1109/TPWRS.2009.2021230](https://doi.org/10.1109/TPWRS.2009.2021230).

