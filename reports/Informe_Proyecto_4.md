---
title: "Proyecto 4: TNEP bi-nivel en un mercado eléctrico"
subtitle: "Validación de Garcés y análisis de incertidumbre en Garver"
date: "15 de noviembre de 2026"
lang: es-CO
---

# Objetivo y alcance

Se implementa el modelo de expansión de transmisión en ambiente de mercado de Garcés, Conejo, García-Bertrand y Romero (2009), con decisiones binarias de inversión en el nivel superior y despacho económico con balance nodal y flujos DC en los niveles inferiores. Se reproducen los casos Garver y RTS-24 publicados, se comprueba parcialmente el caso Garver con viento de Heydari y Barforoushi (2024), y se comparan tres formas de representar incertidumbre de demanda. La consigna dice «Garcés (2014)», pero el artículo adjunto corresponde a **2009**.

Los resultados a continuación distinguen (i) reproducción de resultados numéricos publicados, (ii) verificaciones aproximadas con datos reconstruidos y (iii) discrepancias que permanecen abiertas. Todos los códigos y archivos de datos se incluyen con este informe en el paquete del proyecto.

# Modelo e implementación

Con un plan binario $x$ común a los escenarios, el planificador maximiza el bienestar esperado anual menos la inversión anualizada:

$$\max_x\; 8760\sum_s\pi_s W_s(x)-\mathrm{CRF}\sum_{\ell} C_{\ell}x_{\ell},\qquad \sum_{\ell} C_{\ell}x_{\ell}\le B.$$

Cada mercado maximiza $W_s=$ valor de demanda aceptada $-$ costo de generación $-$ penalización de carga no servida, sujeto a balances, límites de bloques, mínimos de demanda, capacidades y flujos DC. Para reproducir Garcés se emplean CRF aproximado de 0.10, base de 100 MVA y 8760 horas. El código incluye un MILP primal integrado y un MILP primal-dual explícito con igualdad de dualidad fuerte y linealización de productos binario-dual. La equivalencia del primal integrado se basa en que el objetivo superior pondera el mismo bienestar que maximiza cada seguidor, con pesos positivos y escenarios operativamente independientes. La formulación y sus límites se detallan en `reports/formulation_implementation.md`.

# Validación de Garcés

| Caso y métrica | Artículo | Implementación | Estado |
|:--|--:|--:|:--|
| Garver: inversión (M€) | 25.10 | 25.1004 | Coincide |
| Garver: bienestar medio (M€/año) | 292.71 | 292.7141 | Coincide |
| RTS-24 sin contingencias: inversión (M€) | 22.99 | 22.98772 | Coincide |
| RTS-24 sin contingencias: bienestar medio (M€/año) | 742.59 | 742.77728 | Diferencia +0.025% |

En Garver el plan es 2–3 (1), 3–5 (1) y 4–6 (3). En RTS-24 sin contingencias es 6–10, 10–11, 11–13 y 14–23. Las implementaciones primal integrada y primal-dual explícita entregan los mismos planes y objetivos en ambos sistemas, con residuos de dualidad fuerte numéricamente despreciables. Algunas variables duales alcanzan la cota Γ incluso en la sensibilidad Γ=2000; no se interpreta la estabilidad de los objetivos como prueba general de ausencia de restricciones por esa cota.

**RTS-24 con 22 escenarios y contingencias no se reproduce.** El artículo informa inversión de 28.64 M€ y bienestar de 717.97 M€/año. La implementación con penalización de carga no servida 100× obtiene otro plan, 29.31919 M€ y 518.76923 M€/año. Al fijar el plan publicado se obtienen 517.818 M€/año bajo la métrica de bienestar de la formulación. Retirar la penalización *sólo en el recálculo contable*, sin alterar el despacho, da 717.451 M€/año, próximo a la Tabla X. Este diagnóstico sugiere una diferencia de cómputo o reporte, pero no resuelve la diferencia del plan ni sustituye la función objetivo del artículo. El detalle está en `reports/rts24_validation.md`.

# Verificación parcial de Heydari (2024)

La Tabla 4 fue cotejada visualmente: caso 1 añade **2–6 (4), 3–5 (3)**; caso 2 añade **2–6 (4), 3–5 (2), 4–6 (2), 5–6 (2)**. Una versión anterior del proyecto había mezclado columnas y evaluado planes distintos. Ahora el código lee el CSV corregido y despeja el mercado a plan publicado fijo mediante un LP independiente SciPy/HiGHS. La red HVAC usa Garcés y los cinco niveles de carga y seis intensidades eólicas proceden de una digitalización de la Figura 2.

| Caso / pesos de escenarios | Publicado (MUSD/año) | Reconstruido (MUSD/año) | Diferencia |
|:--|--:|--:|--:|
| 1, horas por bloque de carga | 462.64 | 462.34463 | −0.064% |
| 2, horas × 1/6 para viento | 527.62 | 528.88177 | +0.239% |
| 2, 30 pares con igual peso | 527.62 | 452.19717 | −14.295% |

Las energías anuales reconstruidas bajo pesos por duración también son cercanas: en caso 1, consumo 9621.23 frente a 9627.92 GWh; en caso 2, generación fósil 7038.07 frente a 7120.48 GWh, viento 2228.88 frente a 2213.81 GWh y consumo 9332.59 frente a 9400.21 GWh. El caso 2 reconstruido presenta carga no servida de hasta 194.89 MW en algunos estados. El artículo usa horas por bloque en su formulación y afirma también igualdad de pesos para los escenarios del caso Garver; por ello se informan ambas interpretaciones.

Se repitió la sensibilidad ±0.01 p.u. de los puntos digitalizados con el plan correcto. Las perturbaciones comunes exploradas dan 500.53–546.84 MUSD/año, incluyendo el valor publicado. **La cercanía no constituye validación de la expansión óptima:** los planes se fijaron, los datos de línea originales y sus costos en USD no están disponibles, y no se reconstruyeron HVDC ni CVaR de casos 3–4. Véase `reports/heydari_validation.md`.

# Tres métodos de incertidumbre y comparación común

El experimento controlado de Garver conserva precios y costos en EUR de Garcés; escala toda la demanda con un factor común. La curva de duración contiene cinco estados entre 0.334 y 0.914 p.u. Hong PEM 2n+1 emplea tres puntos que igualan cuatro momentos de esa distribución escalar. Monte Carlo muestrea 100 000 veces los mismos cinco estados y los reduce a tres centros con k-means ponderado. Aquí no se incorpora viento a la optimización de inversiones, porque faltan costos comparables en USD.

Comparar sólo los objetivos de optimización de cada método sería engañoso: cada método usa una distribución aproximada distinta. Por ello se fija cada plan y se evalúa sobre **los mismos cinco estados originales**, ponderados por sus horas:

| Plan obtenido con | Objetivo en sus escenarios (M€/año) | Objetivo neto en cinco estados comunes (M€/año) | Pérdida frente al óptimo común (M€/año) |
|:--|--:|--:|--:|
| Curva de duración | 190.08570 | **190.08570** | 0 |
| Hong PEM 2n+1 | 190.10598 | **190.08570** | 0 |
| Monte Carlo reducido | 190.09391 | **23.96820** | **166.11751** |

Duración y PEM eligen dos circuitos 2–6 y uno 3–5, y sus planes tienen el mismo desempeño común. Monte Carlo reducido elige 2–3, 2–6 y 3–5; su mayor centro es 0.8077 p.u., por lo que omite el pico 0.914 p.u. de 1000 horas. Al reaparecer ese pico, su plan deja 15.176 MW de carga no servida. Con la penalización 100×, una pequeña diferencia entre objetivos *internos* se convierte en una gran pérdida bajo la referencia compartida. Una extensión posterior debe preservar explícitamente estados extremos durante la reducción.

# Conclusiones y límites de la entrega

1. Se reproducen los planes y valores principales de Garver y RTS-24 **sin contingencias** del artículo de Garcés. La Tabla V de contingencias Garver está transcrita, pero no se ejecutó como validación independiente.
2. RTS-24 multicontingencia no coincide con el artículo. La diferencia contable del bienestar está localizada; el plan distinto continúa abierto.
3. Con los planes de Heydari correctamente transcritos, sus dos casos HVAC quedan próximos a los valores publicados **bajo pesos por duración y a plan fijo**. No se afirma que se hayan optimizado o reproducido exactamente sus inversiones.
4. Los tres métodos de incertidumbre están implementados. La evaluación común revela que la reducción de Monte Carlo usada aquí elimina un pico decisivo para planificar la expansión.

Las optimizaciones MILP Garcés y los tres métodos son resultados guardados de la ejecución original con Pyomo 6.10.1 / HiGHS 1.15.1. Las nuevas verificaciones con planes fijos y sensibilidades se ejecutaron con SciPy/HiGHS. En el entorno de esta corrección no se volvieron a resolver los MILP originales porque Pyomo no estaba disponible. Cada JSON, script y el manifiesto de resultados permiten distinguir ambas procedencias.

# Reproducción y referencias

Desde la raíz del paquete, instalar `requirements-lock.txt` y el proyecto, según `README.md`. Para regenerar las verificaciones corregidas: `python scripts/run_heydari_reconstructed_market.py`, `python scripts/bound_heydari_digitization_error.py`, `python scripts/evaluate_uncertainty_plans.py` y `python scripts/build_run_manifest.py`. Para recalcular desde cero las tres optimizaciones de incertidumbre se usa `python scripts/compare_uncertainty_methods.py` con Pyomo/HiGHS.

- Garcés, L. P., Conejo, A. J., García-Bertrand, R. y Romero, R. (2009). *A Bilevel Approach to Transmission Expansion Planning Within a Market Environment*. IEEE Transactions on Power Systems, 24(3), 1513–1522. DOI: 10.1109/TPWRS.2009.2021230.
- Garcés Negrete, L. P. (2010). Tesis doctoral adjunta, Apéndice A.3, datos RTS-24.
- Heydari, R. y Barforoushi, T. (2024). *HVDC/HVAC transmission network expansion planning in electricity markets in the presence of wind resources*. Electric Power Systems Research, 229, 110182. DOI: 10.1016/j.epsr.2024.110182.
- Hong, H. P. (1998). *An efficient point estimate method for probabilistic analysis*. Reliability Engineering & System Safety, 59(3), 261–267. DOI: 10.1016/S0951-8320(97)00071-9.
