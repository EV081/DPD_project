# Diccionario de Datos — Clima (Metereología Bogotá)

- Estación de referencia: **80222 — Bogotá / Aeropuerto El Dorado** 
- Periodo: **2026-07-01 - 2026-08-31**.
- Generado por `code/download_clima.py`.

Se producen 3 archivos en `data/clima/` con la misma granularidad que el proceso
TransMilenio (hora = validaciones horarias, día = agregación diaria, semana = agregación
semanal por lunes). El **diario y el semanal se derivan de la serie horaria** (no de la
tabla diaria de Metostat, que llega con `prcp` 100 % NaN).

---

## Variables comunes

Glosario WMO/Metostat, unidades del Sistema Internacional.

| Código | Variable | Unidad | Descripción |
|--------|----------|--------|-------------|
| `temp` | Temperatura | °C | Temperatura del aire en superficie. |
| `tmin` / `tmax` | Temp. mín / máx | °C | Mín/máximo del periodo (agregación). |
| `rhum` | Humedad relativa | % | 0–100. |
| `prcp` | Precipitación | mm | Lluvia acumulada del periodo. |
| `wspd` | Vel. del viento | km/h | Velocidad media del viento. |
| `wpgt` | Racha máxima | km/h | Peak wind gust (frecuente NaN en algunas horas). |
| `wdir` | Dirección del viento | ° | Grados desde el norte (0–360). Solo en granularidad horaria. |
| `pres` | Presión | hPa | Presión atmosférica a nivel de la estación. |
| `cldc` | Cobertura nubosa | octas | 0–8 (8 = cielo cubierto). |
| `coco` | Condición del clima | 1–7 | Código WMO: 1=despejado, 2=poco nublado, 3=parcial, 4=cubierto, 5=neblina, 6=lluvia, 7=viento. Solo horaria. |

---

## `clima_hora_2026-07-01_a_2026-08-31.csv` (1,488 filas = 62 días × 24 h)

| Campo | Tipo | Nulos | Descripción |
|-------|------|-------|-------------|
| `fecha` | datetime | 0 | Timestamp con zona `-05:00` (Bogotá), hora en punto. |
| `temp` | float | 0 | Temperatura horaria (°C). |
| `rhum` | int | 0 | Humedad relativa horaria (%). |
| `prcp` | float | 372 | Precipitación horaria (mm); NaN cuando no llovió (sin registro) o paraguas. |
| `wspd` | float | 0 | Velocidad del viento horaria (km/h). |
| `wpgt` | float | 1,462 | Racha máxima horaria (km/h); mayormente NaN (solo se reporta con rachas). |
| `wdir` | int | 0 | Dirección del viento (°). |
| `pres` | float | 2 | Presión horaria (hPa). |
| `cldc` | int | 0 | Cobertura nubosa (octas 0–8). |
| `coco` | int | 0 | Condición del clima (1–7, ver glosario). |

## `clima_dia_2026-07-01_a_2026-08-31.csv` (62 filas = 62 días)

Derivado de la horaria: `temp` = media, `tmin`/`tmax` = min/max de la hora, `prcp` =
suma de precipitación horaria, resto = promedio. Todos los resultados tienen 0 nulos
salvo `wpgt` (44 NaN en la serie horaria).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `fecha` | datetime | Día (00:00 Bogotá). |
| `temp` / `tmin` / `tmax` | float | Temp. media, mínima y máxima diaria (°C). |
| `rhum`, `wspd`, `wpgt`, `pres`, `cldc` | float | Promedios diarios. |
| `prcp` | float | Precipitación diaria acumulada (mm). |

## `clima_semana_2026-07-01_a_2026-08-31.csv` (10 filas)

Agregación semanal (lunes a domingo) de la horaria. Incluye una semana parcial
(2026-06-29, fuera del rango) y una parcial al final. Mismas variables que el diario,
con `prcp` acumulado por semana.

---

## Notas

- **Zona horaria:** todos los timestamps son `-05:00` (Colombia, sin horario de verano).
- **Día 1 vs Día 2 de TransMilenio:** para unir clima con el dataset, usar `fecha` (día)
  con la `Fecha` de `dataset.csv`; para granularidad horaria, unir por `Hora` de la fecha.
- **Fuente:** Metostat `80222 Bogota/Eldorado`. API nueva (v2): `meteostat.daily()` /
  `meteostat.hourly()` con parámetros `station, start, end, timezone`.
- Reproducible: `python code/download_clima.py` (variables `GRANULARIDAD`, `DESDE`,
  `HASTA`, `ESTACION_ID`, `ZONA_HORARIA`).