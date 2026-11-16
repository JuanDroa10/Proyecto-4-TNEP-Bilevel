# Formulación e implementación del TNEP bi-nivel

## Modelo de Garcés

La formulación sigue el artículo de Garcés et al. (2009), ecuaciones (1)-(19), dual de mercado (21)-(34), condición de dualidad fuerte (35) y reformulación lineal (40)-(45). Las tablas de Garver y RTS-24 se transcribieron a `data/processed/`; el manifiesto de fuentes y los límites de transcripción están en `reports/source_audit.md`.

Variables de primer nivel: $x_{ijc}\in\{0,1\}$, indicador de construcción del circuito candidato $c$ en el corredor $ij$. Variables de mercado por escenario $s$: bloques de generación $g_{gsb}$, bloques de demanda aceptada $d_{dsb}$, carga no servida $u_{ds}$, ángulos $\theta$ y flujos por circuito $f_{ijcs}$.

El objetivo superior alineado es

\[
\max_x\; 8760\sum_s \pi_s W_s - \mathrm{CRF}\sum_{ijc} C_{ij}x_{ijc},
\qquad \sum_{ijc}C_{ij}x_{ijc}\le B.
\]

Cada seguidor $s$ maximiza $W_s=\sum_{db}b_{db}d_{dsb}-\sum_{gb}o_{gb}g_{gsb}-\sum_d\rho_d u_{ds}$, sujeto a cotas de oferta/demanda, consumo mínimo, balance nodal, límites térmicos, relación DC por circuito y ángulo de referencia. Para la reproducción, CRF=0.10, $\sigma=8760$, $\Gamma_{\max}=1000$ y $M=1000$ según los datos configurados del artículo.

## Equivalencia operacional y MILP primal-dual

`src/tnep/models/integrated_primal.py` construye el MILP integrado primal. Dado que los objetivos superiores e inferiores están alineados y cada escenario es independiente condicionado a $x$, maximizar el bienestar ponderado de todos los escenarios da un despacho óptimo para cada seguidor cuando todos los $\pi_s$ son positivos. Este modelo se conserva como referencia rápida.

`src/tnep/models/primal_dual.py` construye la misma parte primal y utiliza `core.lp_dual` de Pyomo para generar explícitamente el dual del LP de mercado combinado. Impone factibilidad dual y primal más igualdad de dualidad fuerte. La formulación combinada es equivalente a los seguidores separados bajo independencia y pesos positivos. Si hubiera escenarios acoplados por restricciones de decisión/recursos operativos, no sería válida esta reducción.

La transformación produce productos bilineales $x_{ijc}\lambda$ sólo en el objetivo dual. Se introducen variables auxiliares $v=x\lambda$ y envolventes McCormick:

\[
0\le v\le \Gamma x,\quad v\le\lambda,\quad v\ge\lambda-\Gamma(1-x),\quad 0\le\lambda\le\Gamma.
\]

Con $x$ binaria, esta linealización es exacta para el límite dual declarado. El valor de $\Gamma$ puede limitar duales factibles si resulta demasiado bajo; por eso cada salida registra el máximo dual, cuántos duales alcanzan $\Gamma$ y el residuo de dualidad fuerte. La igualdad primal-dual con variables duales factibles certifica optimalidad del despacho, aunque la saturación de $\Gamma$ se conserva como advertencia de sensibilidad.

Se hizo una sensibilidad con $\Gamma=2000$ en Garver y RTS-24 sin contingencias. Los dos objetivos y planes (por corredor y cantidad) se mantuvieron iguales a los de $\Gamma=1000$ dentro de 1 EUR. Aun así, algunos duales alcanzan el bound (21 en Garver y 114 en RTS a 2000); se reporta saturación porque la estabilidad numérica del plan/objetivo no prueba que todos los multiplicadores duales posibles estén acotados holgadamente. Resultados: `results/garces_validation/dual_gamma_sensitivity.json`.

La alternativa clásica cambia el objetivo superior a inversión más costo de carga no servida y resuelve una instancia por escenario, en línea con la comparación de Garcés. Las métricas de bienestar se calculan luego con mercado despejado al plan fijo.

## Trazabilidad código-datos

| Elemento | Implementación |
|---|---|
| Variables de expansión, presupuesto y anualización | `integrated_primal.py`, `primal_dual.py` |
| Ofertas, bids y demanda de Garver | `garver_generators.csv`, `garver_demands.csv`, `garver_scenarios.csv` |
| Corredores, reactancias y costos RTS | `rts24_lines.csv`; tesis, Apéndice A.3 |
| Bloques RTS y perfiles | `rts24_generators.csv`, `rts24_demands.csv`, `rts24_scenarios_*.csv` |
| M, Γ, σ, CRF, budget | `*_parameters.json` |
| Comparación y residuo primal-dual | `results/garces_validation/*primal_dual.json` |

## Solución y reproducibilidad

Solver: HiGHS 1.15.1 por Pyomo 6.10.1 / `appsi_highs`. Todas las unidades internas para Garcés son MW, EUR/MWh, EUR, h/año y EUR/h en bienestar horario. Los resultados se guardan como JSON estructurado junto con tiempos. Las ejecuciones se realizan con scripts desde la raíz del proyecto; comandos vigentes están en `README.md`.

## Límites

El enfoque clásico se reproduce por los resultados publicados; la implementación no reconstruye diferencias históricas entre versiones GAMS/CPLEX. RTS multi-contingencia conserva una discrepancia de plan y bienestar; Heydari caso 2, **con el plan corregido y ponderación por duración**, queda a +0.239% del bienestar publicado, pero con pesos uniformes discrepa y la inversión no se ha optimizado. Véanse sus reportes. No se infieren costos HVAC/HVDC ni tipos de cambio ausentes.
