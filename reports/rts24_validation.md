# Validación RTS-24 (Garcés 2009 y tesis 2010)

## Datos y procedencia

Los 41 corredores —34 con circuitos iniciales y siete candidatos— se transcribieron de la Tabla A.3 del Apéndice A.3 de la tesis (página impresa 141). La Tabla A.4 aporta unidades individuales y FOR; A.5 aporta demandas máximas. Las ofertas, bloques de mercado y escenarios se tomaron de las Tablas VI-VII del artículo de 2009. La Tabla A.5 y la Tabla VI del artículo tienen 17 barras con demanda positiva; el párrafo del artículo que dice “16 loads” no coincide con sus propias tablas.

## Caso sin contingencias

Formulación primal integrada con objetivo de bienestar alineado, base 100 MVA y factor de inversión reportado 0.10. HiGHS encontró el óptimo.

| Métrica | Garcés publicado | Actual | Error relativo |
|---|---:|---:|---:|
| Plan | 6-10; 10-11; 11-13; 14-23 | Coincide | Coincide |
| Inversión total (M€) | 22.99 | 22.98772 | -0.0099% |
| Beneficio social medio (M€/año) | 742.59 | 742.77728 | +0.0252% |
| Tiempo reportado/medido | 89.51 s | 4.36 s | No comparable entre hardware/solvers |

La baseline clásica por escenario también coincide en los planes, inversión y bienestar promedio publicados:

| Escenario | Plan | Inversión publicada / actual (M€) | Bienestar medio publicado / actual (M€/año) |
|---|---|---:|---:|
| 1 | 6-7; 7-8; 13-14 | 9.02 / 9.02208 | -2430.44 / -2430.25317 |
| 2 | 6-7 (2); 7-8; 2-8; 11-13 | 17.48 / 17.48372 | 687.17 / 687.35383 |
| 3 | 6-10; 7-8 (2); 13-14 | 9.13 / 9.12624 | -1399.75 / -1399.56617 |

La columna de beneficio social para el escenario individual de la Tabla VIII del artículo no coincide con el re-despeje de mercado a plan fijo, aunque sí coincide el promedio anual. Esta diferencia queda abierta y no se oculta tras el porcentaje del promedio.

### Validación primal-dual explícita

El MILP con dual de mercado y dualidad fuerte resuelve también el caso sin contingencias. Reproduce el mismo plan/costo del primal integrado, con bienestar 742.77728 M€/año y residuo de dualidad fuerte de −8.23×10⁻⁸ EUR/h. Se linealizaron 1,020 productos binario-dual con Γmax=1000. 115 duales alcanzan el bound en una solución óptima; el certificado de igualdad primal-dual se mantiene y este nivel de saturación queda registrado como sensibilidad pendiente. Resultado: `results/garces_validation/rts24_no_contingencies_primal_dual.json`.

Al aumentar Γ a 2000, el objetivo cambia menos de 1 EUR y el plan permanece igual por corredor y cantidad; 114 duales alcanzan el nuevo bound. La sensibilidad queda en `results/garces_validation/dual_gamma_sensitivity.json`.

## Caso multi-contingencia

Los 22 escenarios se implementaron desde la Tabla IX: 16 perfiles de demanda y seis salidas de línea. La suma de los pesos impresos es 0.9997 por redondeo. La variante con penalización 100× (valor configurado en los parámetros reconstruidos) terminó óptimamente, pero no reprodujo la Tabla X:

| Métrica | Garcés publicado | Actual, 100× | Error relativo |
|---|---:|---:|---:|
| Plan | 3-9; 6-10; 7-8 (2); 10-11; 11-13; 13-14 | Distinto: añade 1-2 (2), 13-14 (3), entre otros | — |
| Inversión (M€) | 28.64 | 29.31919 | +2.37% |
| Beneficio social medio (M€/año) | 717.97 | 518.76923 | -27.75% |
| Tiempo | 5.43 h | 263.84 s | No comparable entre hardware/solvers |

El escenario 22 (salida 15-24) genera el mayor problema: bienestar de -0.56457 M€/h y carga no servida. Se resolvió además una sensibilidad con penalización 10×, que produce 28.28133 M€ y 709.65516 M€/año (-1.25% y -1.16% respecto a Tabla X), pero el plan sigue siendo diferente. Esta sensibilidad no se presenta como validación porque 10× no es el dato configurado de referencia. Los resultados señalan una diferencia aún no aislada entre formulación/transcripción/semántica de contingencias y el caso publicado. No se ajustó ningún parámetro para forzar la coincidencia.

Para separar el origen, se despejó el mercado a plan fijo con el plan exacto de Tabla X. Con la configuración 100× obtiene 517.81800 M€/año, aún -27.88% frente a 717.97; la carga no servida máxima es 63.835 MW en escenario 22, demanda D3 (barra 3). La discrepancia, por tanto, ya existe en el seguidor multi-contingencia y no se explica sólo por la elección del plan superior.

### Diagnóstico de la métrica de bienestar

En el escenario 22, el término de penalización asociado a los 63.835 MW de carga no servida equivale a 5,591.959 M€/año dentro de ese escenario. Al retirarlo **sólo para recalcular la métrica**, manteniendo intactos el plan y el despacho del mercado, el bienestar promedio ponderado pasa de 517.818 a 717.451 M€/año; el error frente a Tabla X baja a −0.072%. La renormalización de pesos impresos no explica el resultado (su efecto es aproximadamente 0.03%). Esto indica que la discrepancia de bienestar publicada es casi exactamente consistente con no contabilizar la penalización de carga no servida en el agregado, aunque el artículo define el bienestar del seguidor incluyendo esa penalización. Este cálculo es un diagnóstico contable, no una formulación corregida ni una validación de Tabla X.

Se intentó también optimizar el nivel superior usando esa métrica bruta como prueba de sensibilidad. El MILP no produjo una solución verificable dentro del tiempo de investigación disponible y se detuvo sin guardar resultados. Por ello no se afirma que esta discrepancia explique el plan de expansión distinto. El modelo principal conserva la penalización 100× que especifica el artículo y mantiene explícita la diferencia: el plan y bienestar del modelo son 29.31919 M€ y 518.76923 M€/año (+2.37%, −27.75%); el plan publicado fijado da 28.64 M€ y 517.818 M€/año bajo la métrica neta.

La sensibilidad con 10× da 697.48765 M€/año para el plan publicado fijo (−2.85%) y reduce el error de la optimización libre, pero 10× contradice el parámetro explícito del artículo y no es una corrección aceptable. No se ajustó esa penalización para forzar la coincidencia.

Al mantener el plan 100× fijado y renormalizar a posteriori los pesos impresos (suma 0.9997), el bienestar neto pasa de 517.818 a 517.973 M€/año (+0.03%). Se cotejaron las seis salidas de línea de Tabla IX contra las restricciones de circuito: se desconecta el circuito existente del corredor indicado y se impone flujo cero; el resto de los circuitos permanece disponible. Las zonas, factores de demanda, presupuestos, mínimo de 90%, tope de tres circuitos y límite de inversión coinciden con el texto/tablas del artículo. La causa más probable para el desajuste de bienestar es una diferencia en el cómputo/reportado de la penalización de r en Tabla X. La causa del plan discrepante permanece sin identificar, y no debe declararse resuelta sin un registro de corrida o confirmación de los autores sobre esa métrica.

## Archivos

- Datos: `data/processed/rts24_lines.csv`, `rts24_generators.csv`, `rts24_demands.csv`, `rts24_scenarios_no_contingencies.csv` y `rts24_multicontingency_scenarios.csv`.
- Resultados: `results/garces_validation/rts24_no_contingencies_integrated.json`, `rts24_no_contingencies_cost_min.json`, `rts24_multicontingency_integrated.json` y `rts24_multicontingency_ls10_sensitivity.json`.
- Ejecuciones y diagnósticos: `scripts/run_rts24_integrated.py`, `scripts/run_rts24_cost_min.py`, `scripts/run_rts24_primal_dual.py`, `scripts/run_rts24_multicontingency.py`, `scripts/run_rts24_multicontingency_ls10_sensitivity.py`, `scripts/diagnose_rts24_published_multicontingency_plan.py` y `scripts/analyze_rts24_table_x_welfare_accounting.py`.
- Salida del nuevo diagnóstico contable: `results/garces_validation/rts24_table_x_welfare_accounting_diagnostic.json`.

