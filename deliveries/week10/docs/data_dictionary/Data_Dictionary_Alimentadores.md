# Diccionario de datos — Alimentadores (COSAC)

Archivos: `data_processed/clean/alimentador_hora.parquet` y `data_processed/clean/alimentador_tarifa.parquet`
Origen: `COSAC - ALIMENTADOR` (hoja del libro `4950-2026-02-0012640.xlsx`)
Filas: 1,640,842 (hora) y 804,864 (tarifa) · Periodo: 2025

## Qué representa

Los **alimentadores** son los buses que conectan a los pasajeros con las estaciones del
Metropolitano. A diferencia de las troncales, aquí sí se conoce el **paradero** y el
**sentido**, porque el usuario valida en un punto de bajada/sublida concreto.

**Grano:** una fila por (fecha, ruta, sentido, nº de paradero, hora), sumando los tipos
de tarifa.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | datetime64 | Día de operación |
| `anio` | Int16 | Año (2025) |
| `mes` | Int8 | Mes 1–12 |
| `dia_semana` | str | `LUN`…`DOM` |
| `tipo_dia` | str | `LAB`, `SAB`, `DOM` |
| `semana_iso` | Int16 | Semana ISO del año |
| `feriado` | str | Nombre del feriado o `None` |
| `es_feriado` | bool | `True` si es feriado nacional |
| `linea` | string | Número de línea (30 distintas, p. ej. `305`, `308`, `317`) |
| `ruta` | string | **Nombre** de la ruta (p. ej. `Alisos`, `Villa El Salvador`) |
| `sentido` | str | Sentido tal como viene en el archivo. **En esta hoja el archivo ya usa el formato `N->S` / `S->N`**, así que coincide con `sentido_norm`. |
| `sentido_crudo` | string | Copia de `sentido` antes de normalizar |
| `sentido_norm` | str | Sentido normalizado. En alimentadores solo hay dos valores: `N->S` y `S->N` (no existen `E->O` ni `O->E`, a diferencia de corredores). |
| `eje` | str | Eje del recorrido: aquí **siempre `NS`**, nunca `EO`. |
| `n_paradero` | string | Número de paradero |
| `paradero` | string | Nombre del paradero / estación |
| `hora` | int64 | Hora 0–23 |
| `validaciones` | float64 | Validaciones en esa unidad-hora |

### Sobre `ruta` vs `linea`

`linea` es el **código** numérico de la ruta (`305`), `ruta` es el **nombre**
(`Alisos`). Son cosas distintas: hay 30 líneas y 27 nombres de ruta. Al modelar,
conviene usar `ruta` como unidad (es lo que la gente reconoce) y `linea` como
atributo.

## `alimentador_tarifa.parquet`

Desglose tarifario, a nivel (fecha, ruta, hora, tarifa) — **sin** desglose por
paradero, porque el archivo mezcla las tarifas dentro de las columnas horarias.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | datetime64 | Día |
| `ruta` | string | Nombre de la ruta |
| `hora` | int64 | Hora |
| `tipo_tarifa` | str | `General`, `Universitario`, `Escolar`, `Libre` |
| `validaciones` | float64 | Validaciones de esa tarifa |

Distribución real de la mezcla (2025):

| Tarifa | Participación |
|--------|--------------|
| General | 83.3% |
| Universitario | 13.8% |
| Escolar | 2.1% |
| Libre | 0.7% |

La composición **varía con la hora, y no de forma monótona**. El universitario es
mínimo en la madrugada temprana y máximo al cierre del servicio:

| Franja | Universitario |
|--------|---------------|
| 04h | 5.3% |
| 05h | 9.1% |
| 06–11h (media) | 13.4% |
| 12–14h (media) | 15.8% |
| 19–21h (media) | 14.2% |
| 22h | 17.7% |
| 23h | 19.4% |

Además la hora 00h está al 17.1%, y las horas **01, 02 y 03 no tienen ningún dato**: la
serie arranca a las 00h, se corta hasta las 04h y termina a las 23h. Por eso
`tipo_tarifa` es una variable con señal propia, pero **no se debe hacer un perfil
horario esperando 24 horas seguidas**.

## Notas de calidad

- **Cobertura 85%**: los alimentadores **nunca** alcanzan los 365 días. El máximo son 364
  días y la mediana también 364, así que el problema no es de días sueltos sino de que
  hay rutas muy por debajo: el rango va de 0.3% a 99.7% de cobertura.
- **Mucha dispersión interna**: el coeficiente de variación mediano de la demanda
  diaria por ruta es 44.5% (rango 29.5%–89.8%), y el día más fuerte de una ruta tiene de
  media **31 veces** las validaciones del día más débil (hasta 506 veces en el peor caso).
  Buena parte de eso es falta de datos, no variabilidad real del servicio: por eso el
  filtro de cobertura del 90% es obligatorio.
- Solo aparece el eje `NS`: los alimentadores son todos norte-sur. Los corredores usan
  `EO` en parte de sus rutas.
- `tipo_dia` **lo calculamos nosotros** a partir de la fecha (esta hoja no trae la
  columna `TIPO DE DÍA` del archivo, a diferencia de corredores) y `es_feriado` /
  `feriado` vienen del calendario. Los feriados tampoco se distinguen en el archivo.

## Lo que no se puede derivar

Igual que en las troncales: **no hay `bus_id`, ni headway, ni hora individual de
abordaje**. Por lo tanto no es posible reconstruir el aforo de un bus. La capacidad
oficial de los alimentadores (80 o 40 pasajeros) **no se pudo verificar en una fuente
oficial durante esta semana**, por lo que no se incluye en los datos: inventarla
produciría un aforo falso.
