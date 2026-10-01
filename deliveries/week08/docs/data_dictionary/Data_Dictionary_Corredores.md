# Diccionario de datos — Corredores Complementarios

Archivo: `data_processed/clean/corredores_hora.parquet`
Origen: `CORREDORES COMPLEMENTARIOS` (hoja del libro `4950-2026-02-0012640.xlsx`)
Filas: 4,532,529 · Columnas: 19 · Periodo: 2025

## Qué representa

Los **corredores** son los buses troncales del Metropolitano identificados por un
número (301, 302, …, 412) y separados por color: Azul, Rojo y Morado. Conectan con
las líneas del Metro y con los alimentadores.

**Grano:** una fila por (fecha, ruta, código de paradero, sentido, hora).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | datetime64 | Día de operación |
| `anio` | Int16 | Año (2025) |
| `mes` | Int8 | Mes 1–12 |
| `dia_semana` | str | `LUN`…`DOM` |
| `tipo_dia` | str | Tipo de día **derivado** por nosotros (ver más abajo) |
| `semana_iso` | Int16 | Semana ISO del año |
| `feriado` | str | Nombre del feriado o `None` |
| `es_feriado` | bool | `True` si es feriado nacional |
| `ruta` | string | Número de corredor (p. ej. `301`) — **texto, no número** |
| `cod_paradero` | string | Código del paradero |
| `paradero` | string | Nombre del paradero |
| `sentido` | str | Sentido crudo del archivo |
| `sentido_crudo` | string | Copia de `sentido` antes de normalizar |
| `sentido_norm` | str | `N->S`, `S->N`, `E->O`, `O->E` |
| `eje` | str | `NS` o `EO` |
| `hora` | int64 | Hora 0–23 |
| `validaciones` | float64 | Validaciones en esa unidad-hora |
| `tipo_dia_archivo` | str | Valor crudo de la columna `TIPO DE DÍA` del archivo |
| `tipo_dia_coincide` | bool | Control de calidad: ¿`tipo_dia_archivo` coincide con el día real? |

## `TIPO DE DÍA` es redundante (y se conserva como control)

El archivo trae una columna `TIPO DE DÍA` con valores tipo `LUN`, `MAR`, etc. La
verificamos contra el día de la semana real de la fecha:

```
Dia de la semana (calculado) -> TIPO DE DIA (del archivo):
LUN -> ['LUN']
MAR -> ['MAR']
...
Filas donde coincide: 100.0000%
```

**Conclusión: la columna es 100% derivable de la fecha.** No aporta información de
feriados ni de días especiales. Por eso el EDA de corredores:

- Calcula `tipo_dia` por su cuenta (para no depender de una columna redundante).
- **Conserva** `tipo_dia_archivo` y añade `tipo_dia_coincide` como **control de
  calidad de la carga**: si algún día dejara de cuadrar, sería un error de carga del
  archivo y saltaría a la vista.

Esto es especialmente importante porque los **feriados no están marcados** por esta
columna: un feriado nacional aparece como un día laborable normal. Hay que usar
`es_feriado` / `feriado`.

## Normalización de sentidos

Estos son los valores **realmente presentes** en `sentido` y a qué se mapean. El
recuento viene de una agregación sobre las 4,532,529 filas:

| `sentido` (crudo) | `sentido_norm` | `eje` | Filas |
|--------------------|----------------|-------|-------|
| `NS` | `N->S` | `NS` | 1,328,853 |
| `SN` | `S->N` | `NS` | 1,264,395 |
| `EO` | `O->E` | `EO` | 968,451 |
| `OE` | `E->O` | `EO` | 967,641 |
| `IDA` | `N->S` | `NS` | 2,288 |
| `VUELTA` | `S->N` | `NS` | 889 |
| `257 A` | `None` | `None` | 12 |

Dos cosas que conviene entender aquí:

1. **`IDA` y `VUELTA` no son sentidos, son ida y vuelta.** El archivo los usa como
   etiquetas de dirección del recorrido, no como un tercer y cuarto eje. Se mapearon al
   sentido geográfico que les corresponde (IDA = N→S, VUELTA = S→N) para que no queden
   fuera de los agregados por sentido. Y no es una decisión arbitraria: **son las únicas
   dos rutas que los usan**, cada una de forma exclusiva.
2. **`257 A` es basura del archivo, no un sentido.** Son 12 filas de la ruta 257 donde
   el valor parece un encabezado o un artefacto de carga que se coló en la columna
   `sentido`. Se dejan con `sentido_norm = None` en vez de inventarles un eje. La ruta
   257 entera son solo esas 12 filas en 2 días (0.5% de cobertura, 70 validaciones), así
   que no hay nada que rescatar.

> Ojo: `sentido`, `sentido_crudo` y `sentido_norm` son las **tres** columnas de sentido
> y son distintas. `sentido` == `sentido_crudo` (el archivo traía duplicada la
> información); `sentido_norm` es la única normalizada. Usa `sentido_norm` para analizar
> y `sentido` solo para auditar contra la fuente.

## Notas de calidad

- **Cobertura 63%**: es la fuente con peor cobertura. Solo 12 de 26 rutas tienen
  >90% de los días de 2025; hay rutas con **1 a 5 días sueltos**. Promediar sin filtrar
  produce nonsense.
- **Varios tamaños de columna**: esta hoja es la más grande (700,892 filas crudas × 32
  columnas → 4.5M filas al pasar a formato largo) y tarda ~143 s en leerse.
- **Balance de sentidos: fuerte en algunas rutas.** De las 25 rutas con `sentido_norm`
  válida, **22 reportan los dos sentidos** y ahí sí están relativamente parejas: el
  lado con más validaciones concentra entre 50.0% y 70.1% del total, es decir ratios de
  1.00 a 2.34. Las **3 restantes reportan un solo sentido** (el 100% de su volumen), así
  que para ellas no existe comparación posible y cualquier supuesto de simetría es falso:

  | Ruta | Solo este sentido | Validaciones | Cobertura |
  |------|-------------------|--------------|-----------|
  | `3180` | `N->S` (vía `IDA`) | 493,757 | 67.4% |
  | `2011` | `O->E` | 92,767 | 47.7% |
  | `3090` | `S->N` (vía `VUELTA`) | 24,931 | 34.5% |

  Ninguna de las 3 pasa el filtro de cobertura del 90%, por eso no aparecen en la tabla
  de balance de `eda_corredores.ipynb`. Ese notebook sí muestra que **dentro** de las 12
  rutas confiable hay 3 fuera de [0.77, 1.30]: `371` en 1.60, `406` en 0.66 y `412` en
  0.61. Conclusión: la simetría es la norma pero no está garantizada, y
  `sentido_norm` **sí aporta señal**.
- **Rutas del portal que no existen en los datos**: 4 de las 20 páginas del portal
  (`Rojo/257`, `Rojo/409`, `Morado/401`, `Morado/601`) devuelven error del SRA; el
  scraper las omite.

## Lo que no se puede derivar

- **Aforo / ocupación**: sin `bus_id` ni headway, y con truncamiento por saturación.
- **Frecuencia de las 12 rutas del dataset**: portal/apps no publican intervalos
  estáticos. Externas: SE08 ≈ 5 min (prensa 2025, fuera del Excel) y 404 ≈ 15 min
  (tesis UPC 2023, confianza baja). Ver `frecuencias_corredores_prensa.csv` y
  `docs/analisis.md`.
