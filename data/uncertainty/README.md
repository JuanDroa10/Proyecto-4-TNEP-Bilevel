# Datos de incertidumbre Heydari (reconstrucción de Figura 2)

`heydari_fig2_load_points.csv` y `heydari_fig2_wind_points.csv` son una digitalización manual de la Figura 2 (página PDF 8) del artículo de Heydari y Barforoushi (2024). No son datos suplementarios oficiales. Los factores se midieron contra los ejes de la figura con calibración por píxeles; se conserva el píxel vertical leído y se asigna una incertidumbre de digitalización de ±0.01 p.u.

El script `scripts/build_heydari_fig2_scenarios.py` combina cinco bloques de carga con seis niveles eólicos por bloque. Usa el multiplicador de demanda 2.2 que informa la sección 4.1.1 y capacidad eólica de 500 MW por parque. El parque del bus 6 se calcula como 1.1 veces el índice del bus 4, según el artículo.

La ponderación no queda inequívoca en el texto: la formulación da horas `N_t` por bloque y pesos de escenarios eólicos `delta(omega)`, mientras el caso de estudio dice que todos los escenarios tienen igual peso. El CSV resultante conserva dos lecturas para análisis de sensibilidad: horas del bloque multiplicadas por probabilidad condicional eólica 1/6, y peso uniforme 1/30 para todos los pares bloque-estado.

Para reproducir por completo los casos HVAC/HVDC siguen faltando datos oficiales de las alternativas HVDC (susceptancia/capacidad/costo) y las cifras exactas de la curva. La red HVAC de Garcés puede usarse como reconstrucción declarada, pero no se debe presentar como el insumo exacto de Heydari.
