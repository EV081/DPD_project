# Diccionario de datos — Troncales del Metropolitano

Archivo: `data_processed/clean/troncal_hora.parquet`
Origen: `COSAC - TRONCAL` (hoja del libro `4950-2026-02-0012640.xlsx`)
Filas: 342,703 · Columnas: 11 · Periodo: 2025 completo

## Qué representa

Las **troncales** son los buses articulados (tipo SOYUZ) que circulan por los ejes
principales (Vía Evitamiento / Gran Vía). Se reportan **por estación**, porque el
usuario valida al subir o bajar en una estación troncal, no a bordo de un bus
identificado.

**Grano:** una fila por (fecha, estación, hora).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | datetime64 | Día de operación, medianoche normalizada |
| `anio` | Int16 | Año de `fecha` (2025) |
| `mes` | Int8 | Mes 1–12 |
| `dia_semana` | str | Día de la semana en español: `LUN`, `MAR`, `MIÉ`, `JUE`, `VIE`, `SÁB`, `DOM` |
| `tipo_dia` | str | `LAB`, `SAB`, `DOM` |
| `semana_iso` | Int16 | Número de semana ISO del año |
| `feriado` | str | Nombre del feriado, o `None` si no es feriado |
| `es_feriado` | bool | `True` si la fecha es feriado nacional |
| `estacion` | str | Nombre de la estación troncal (46 en total) |
| `hora` | int64 | Hora de la validación, 0–23 |
| `validaciones` | int64 | Número de validaciones registradas en esa estación-hora |

## Notas de calidad

- **Cobertura 99%**: 45 de 46 estaciones tienen los 365 días de 2025. La excepción es
  **Las Vegas**, con 197 días (54.0%), identificable en `calidad_cobertura.csv`.
- **Los únicos nulos están en `feriado`**, y son esperados: `feriado` vale `None` en el
  97.1% de las filas porque solo 11 días de 2025 son feriado (10,030 filas). **No hay
  nulos en ninguna otra columna** y no hay valores negativos: `validaciones` va de 1 a
  17,477.
- **Grano único, sin duplicados**: 0 filas repetidas en (fecha, estación, hora).
- `tipo_dia` distingue `LAB`, `SAB` y `DOM`. **Los feriados no se distinguen** en esa
  columna: un feriado aparece como día laborable. Por eso se agregan `feriado` y
  `es_feriado` desde el calendario. Los 11 feriados de 2025 presentes son Año Nuevo,
  Jueves y Viernes Santo, Día del Trabajo, San Pedro y San Pablo, Fiestas Patrias,
  Santa Rosa de Lima, Combate de Angamos, Todos los Santos, Inmaculada Concepción y
  Navidad.
- El archivo **no** trae desglose por tarifa; ese desglose solo existe para
  alimentadores y para la L1.
- El archivo **no** trae `bus_id` ni frecuencia, por lo que no se puede calcular
  ocupación ni pasajeros por bus.

## Lo que no se puede derivar

- **Aforo u ocupación**: las validaciones son abordajes y se truncan cuando el bus va
  lleno. En hora punta el conteo subestima la demanda real.
- **Pasajeros por bus**: no hay identificador de vehículo ni intervalo de salida en el
  archivo.
- **Sentido de viaje**: las troncales no reportan sentido; solo estación-hora.
