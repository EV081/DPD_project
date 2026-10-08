# Diccionario de datos — Metro Línea 1

Archivos: `data_processed/clean/metro_l1_hora.parquet` y `data_processed/clean/metro_l1_total_hora.parquet`
Origen: 12 libros Excel mensuales en `data/AIP -E- 0302-2026-02-0060693/Validaciones_01.2024-01.2026/2025/`
Filas: 307,363 (con tarifa) y 169,921 (agregado) · Periodo: 2025 completo

## Qué representa

La Línea 1 del Metro de Lima es la fuente **más limpia y completa** del lote: 26
estaciones, los 365 días de 2025, 18 franjas horarias (05–22h). Se reporta por
estación, hora y **tipo de tarifa**.

**Grano:** una fila por (fecha, estación, hora, tipo de tarifa) en el archivo con
tarifa (307,363 filas, sin duplicados), y por (fecha, estación, hora) en el agregado
(169,921 filas, también sin duplicados).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | datetime64 | Día de operación |
| `anio` | Int16 | Año (2025) |
| `mes` | Int8 | Mes 1–12 |
| `dia_semana` | str | `LUN`…`DOM` |
| `tipo_dia` | str | `LAB`, `SAB`, `DOM` — **el archivo sí distingue el sábado** |
| `semana_iso` | Int16 | Semana ISO del año |
| `feriado` | str | Nombre del feriado o `None` |
| `es_feriado` | bool | `True` si es feriado nacional |
| `estacion` | str | Nombre de la estación (26) |
| `hora` | Int16 | Hora 5–22 (el metro no opera de madrugada) |
| `intervalo` | str | Etiqueta de la franja horaria del archivo (`5-6 h`, `18-19 h`, …) |
| `tipo_tarifa` | string | `Adulto` o `Universitario` |
| `validaciones` | float64 | Validaciones |

`metro_l1_total_hora.parquet` tiene las mismas columnas **menos** `intervalo` y
`tipo_tarifa`: es la suma de las tarifas, una fila por estación-hora.

## Aviso importante: los domingos no traen tarifa universitaria

Esta es la trampa más sutil del lote. El archivo trae un desglose tarifario que en los
domingos **no existe**: el conteo de filas por tipo de día y tarifa es

| tipo_dia | Adulto (filas) | Universitario (filas) |
|----------|-----------------|----------------------|
| `DOM` | 24,040 | **1** |
| `LAB` | 121,620 | 114,869 |
| `SAB` | 24,252 | 22,581 |

En los **domingos** prácticamente no hay filas de tarifa universitaria (1 en todo el
año, con 1 validación). No significa que no haya pasajeros universitarios: significa
que el archivo no los reporta ese día.

**Consecuencia práctica:** si promedias filas para comparar días, el domingo parecería
**más** mover de lo que mueve (promedias una sola tarifa grande en vez de la suma de
dos). Por eso el análisis de demanda debe usar siempre `metro_l1_total_hora.parquet`, y
el cálculo de mezcla tarifaria debe **excluir los domingos**.

Mezcla tarifaria real (excluyendo domingos): **Adulto 94.6%**, **Universitario 5.4%**.
Ese 5.4% es además la magnitud del sesgo del domingo: si los domingos tuvieran la
misma mezcla, el domingo estaría subestimado en ese orden.

## Sobre el campo `Periodo` de los Excel

El metadato `Periodo` de los libros mensual apunta al mes **siguiente** al de los
datos. Para el período real hay que usar siempre la columna `Fecha`.

## `tipo_dia` sí distingue el sábado

A diferencia de los corredores, aquí el archivo codifica `SAB` aparte de `LAB`. Y los
datos lo respaldan: el sábado mueve **1.01×** lo que el lunes (casi idéntico), mientras
el domingo cae a **0.55×**. Agrupar "sábado y domingo = fin de semana" es un error en
la mitad de los días del fin de semana.

## Frecuencia y capacidad (datos oficiales externos)

Estos **no** vienen en los Excel; se tomaron de comunicados de la ATU y están en
`data/fuentes/frecuencias_l1_oficial.csv`, `capacidad_vehiculos.csv` y
`aforos_publicados.csv`.

| Dato | Valor | `confianza` |
|------|-------|-------------|
| Viajes L–Sáb | 510/día, 3–4 min en punta | alta |
| Viajes sábado | 510/día, 3–10 min según horario | alta |
| Viajes domingo | 292/día, 6–12 min | alta |
| Pasajeros por tren | 428–512 (rango publicado, dic 2020) | alta |
| Aforo oficial publicado | 17% actual (dic 2020), 36% con flota Alstom, 43% con Ansaldo | alta |
| Capacidad nominal del tren | 1,200 pasajeros | **media** (derivado) |

El 1,200 es una extrapolación nuestra a partir del rango 428–512 y la ocupación
36–43% del comunicado, no un dato oficial. Ver el detalle en
`Data_Dictionary_Fuentes_Web.md`.

## Lo que no se puede derivar: ocupación

Se **no** genera un `estimate_occupancy.py`, y estas son las razones concretas:

1. **No sabemos qué cuenta una validación.** Si es un paso por torniquete, el total
   diario es el doble que el número de pasajeros que viajan, y cualquier ocupación
   sale inflada al menos al doble.
2. **La frecuencia está agregada.** 510 viajes/día no permite saber cuántos trenes
   hubo a las 8:00, que es lo que haría falta para una ocupación por hora.
3. **Saturación.** Cuando el tren va lleno, quien no logra subir no valida. El cociente
   subestima la demanda real **justo en la punta**, que es donde importa.
4. **El único aforo oficial** es un dato puntual de diciembre de 2020, no una serie.

Lo que sí se puede calcular es **capacidad instalada** (viajes × pasajeros/tren) como
contexto. El EDA lo muestra explícitamente etiquetado como cota superior, no como
ocupación.
