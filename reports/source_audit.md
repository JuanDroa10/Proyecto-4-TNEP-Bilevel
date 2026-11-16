# Auditoría de fuentes y transcripciones

Fecha de revisión original: 2026-11-06. Corrección de Tabla 4: 2026-11-15 (America/Bogota).

## Garcés et al.

El artículo localizado es *A Bilevel Approach to Transmission Expansion Planning Within a Market Environment*, IEEE Transactions on Power Systems, vol. 24, no. 3, agosto de 2009, pp. 1513-1522, DOI 10.1109/TPWRS.2009.2021230. Por tanto, la referencia bibliográfica del artículo es 2009; si el proyecto cita 2014, esa fecha requiere una fuente distinta o debe corregirse.

El artículo incluye datos tabulados para Garver, RTS-24 sin contingencias y RTS-24 con contingencias, además de planes, inversiones, beneficios sociales y tiempos obtenidos con GAMS/CPLEX 11.0. Para Garver publica M=Gamma_max=1000, sigma=8760, factor de recuperación tratado aproximadamente como 10%, tasa del 10%, horizonte de 25 años y presupuesto de 30 M€. El caso RTS-24 sin contingencias usa presupuesto de 23 M€; el caso de contingencias usa 30 M€ y 22 escenarios.

## Heydari y Barforoushi (2024)

El PDF disponible es *HVDC/HVAC transmission network expansion planning in electricity markets in the presence of wind resources*, Electric Power Systems Research 229 (2024), 110182, DOI 10.1016/j.epsr.2024.110182. Es un modelo estocástico bi-nivel con HVAC/HVDC y riesgo CVaR por incertidumbre eólica; no es una comparación entre PEM, curva de duración y Monte Carlo.

El estudio Garver usa 5 bloques de demanda, 6 intensidades eólicas por bloque, dos parques en buses 4 y 6, coeficiente de demanda 2.2, hasta cuatro líneas HVAC y dos HVDC por corredor, y presupuesto de 400 M$. La Tabla 4 reporta cuatro casos. Se cotejaron visualmente sus columnas: caso 1 añade 2–6 (4), 3–5 (3); caso 2 añade 2–6 (4), 3–5 (2), 4–6 (2), 5–6 (2). El caso 3 además incluye 3–6 (1) y HVDC 2–6 (1). La reconstrucción HVAC utiliza la Tabla I de Garcés y los precios de Tabla 3; Figura 2 se digitalizó manualmente con error de lectura exploratorio ±0.01 p.u. No es una reproducción de los datos originales.

Los parámetros HVAC/HVDC originales de [41] y la hoja de cálculo complementaria siguen sin estar disponibles en los documentos; en particular faltan susceptancia, capacidad y costo de candidatos HVDC. Además, la Tabla 4 de Heydari informa costos en M$ mientras los costos de línea de la Tabla I de Garcés están en k€. Sin los datos originales/currency basis no se pueden comparar directamente las inversiones ni reproducir los casos 3-4, que incluyen HVDC. Los casos 1-2 se pueden estudiar con la red HVAC reconstruida, manteniendo visible esta diferencia de fuente y moneda.

## Pendientes de extracción/verificación

- Garver se resolvió con base de 100 MVA y reprodujo la Tabla IV del artículo hasta el redondeo; el informe de formulación documenta las unidades y el escalamiento empleados.
- RTS-24: el Apéndice A.3 de la tesis (pp. 141-143) contiene los 34 corredores existentes y siete candidatos, con capacidad, reactancia, costo, número de circuitos existentes y FOR; los Apéndices A.4/A.5 contienen unidades y demanda máxima. Las ofertas/demandas por bloques y escenarios vienen de las Tablas VI/VII/IX del artículo de Garcés. La tabla de mercado tiene 17 filas con demanda positiva, lo cual coincide con A.5 aunque el texto del artículo dice “16 loads”.
- RTS-24 multi-contingencia: la Tabla IX muestra cada peso de los 21 escenarios posteriores como 0.0357; con el peso 0.25 del primer escenario, el total mostrado suma 0.9997 por redondeo. En el plan publicado, normalizar a posteriori altera el bienestar +0.03% únicamente; la discrepancia con Tabla X persiste porque también aparece al despejar el mercado con ese plan fijo.
- Con planes corregidos de Tabla 4, el despeje del caso 1 queda a −0.064% y el caso 2 a +0.239% con pesos por duración; con 30 pesos iguales, el caso 2 queda a −14.295%. Sigue siendo una verificación aproximada a plan fijo, no una optimización de inversiones. Ver `reports/heydari_validation.md`.
- No usar valores HVDC inventados: registrar los casos 3-4 como no reproducibles hasta obtener los datos oficiales de [41] o el suplemento.
- La conversión de kEUR a EUR, la anualización por CRF, las horas y ponderaciones se documentan en `reports/formulation_implementation.md`; no se mezclan EUR y USD en la optimización comparativa de incertidumbre.
- RTS-24 sin contingencias valida dentro de 0.03%; multi-contingencia no reproduce con penalización 100×: diferencia de +2.37% en inversión y -27.75% en bienestar neto. Para el plan publicado fijado, sumar de vuelta después del despacho la penalización ponderada de carga no servida cambia 517.818 a 717.451 M€/año, a −0.072% de Tabla X. Esto localiza casi toda la discrepancia del bienestar en la métrica contable de la carga no servida, pero dicha métrica bruta contradice las ecuaciones (1) y (5), que incluyen la penalización. El plan óptimo sigue sin reproducirse; la variante de optimización con bienestar bruto excedió el tiempo de diagnóstico y no generó resultado verificable. La sensibilidad 10× no sustituye el parámetro 100× reportado.
- La formulación primal-dual explícita reprodujo Garver y RTS-24 sin contingencias, con residuo de dualidad fuerte <1e-7 EUR/h. Curva de duración, PEM 2n+1 y Monte Carlo reducido se optimizaron para demanda; una nueva evaluación de los planes con los mismos cinco estados reveló gran pérdida por el pico omitido en la reducción de Monte Carlo.
- Con el plan Heydari 2 corregido, el barrido común ±0.01 p.u. produce 500.53–546.84 MUSD/año con pesos por duración. El valor publicado de 527.62 está dentro del intervalo explorado; no se infiere la causa precisa de la pequeña diferencia nominal.
- El CSV de Garver Tabla V corrigió la fila de contingencia 2–3: Tabla V imprime `2–3; 3–5; 4–6 (3)`. Es un dato de referencia; la Tabla V aún no se ha reproducido computacionalmente en esta entrega.

