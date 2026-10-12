# Diccionario de datos — Fuentes web

Carpeta: `data/fuentes/` · Generada por `code/scripts/download_transport_pages.py`

Estos CSV son **contextualización**, no el dataset principal. Sirven para interpretar
las validaciones (horarios, frecuencias, capacidades) y para documentar de dónde sale
cada dato oficial.

> **Regla de oro de esta carpeta:** toda fuente no oficial está marcada con
> `no_oficial=True` y `confianza="baja"`.
---

## Inventario

| Archivo | Filas | Fuente | Oficial |
|---------|-------|--------|---------|
| `servicios_por_estacion.csv` | 44 | portal.atu.gob.pe | Sí |
| `horarios_servicios.csv` | 86 | portal.atu.gob.pe | Sí |
| `paraderos_corredores.csv` | 1,111 | portal.atu.gob.pe | Sí |
| `horarios_corredores.csv` | 39 | portal.atu.gob.pe | Sí |
| `horario_linea1.csv` | 2 | portal.atu.gob.pe | Sí |
| `frecuencias_l1_oficial.csv` | 3 | gob.pe (nota ATU) | Sí |
| `capacidad_vehiculos.csv` | 2 | gob.pe (notas ATU) | Sí |
| `aforos_publicados.csv` | 4 | gob.pe (nota ATU) | Sí |
| `frecuencias_referencia.csv` | 19 | metrolima.info | **No** |
| `frecuencias_corredores_prensa.csv` | 5 | RPP / Radio Nacional / Infobae / UPC | Prensa/tesis |
| `auditoria_apps_frecuencia.csv` | 6 | TuRuta, Moovit, Maps, operadores | Auditoría |

---

## Columnas comunes a casi todos

| Columna | Descripción |
|---------|-------------|
| `url` | URL exacta de la que se extrajo la fila. Sin esto no se puede auditar. |
| `confianza` | `alta` = dato oficial literal; `media` = valor derivado del comunicado; `baja` = fuente de terceros. |
| `no_oficial` | `True` en `frecuencias_referencia.csv`. La prensa de corredores no usa esta columna; va con `confianza=media`. |
| `metodo` | Cómo se obtuvo: `scraping` (del portal), `manual_verificado` (transcrito del comunicado) o `derivado_del_comunicado` (calculado a partir del comunicado). |
| `linea` / `sistema` / `servicio` | Clave del elemento según el archivo. |
| `descripcion` | Texto original de la fuente, sin interpretar. |
| `nota` | Solo en `aforos_publicados.csv`: por qué el dato no es una serie. |

> **Ojo con `confianza`:** no todos los valores "oficiales" son igual de firmes.
> La capacidad de 1,200 pasajeros del tren L1 es un **cálculo nuestro** a partir de un
> comunicado que solo da un rango de ocupación; por eso va como `media` y
> `derivado_del_comunicado`, no como dato oficial. Lo truly oficial es el rango 428–512
> de `aforos_publicados.csv`, que sí es `alta` / `manual_verificado`.

---

## Fuentes oficiales

### `servicios_por_estacion.csv` — 44 estaciones
El nombre del archivo refleja que el portal tiene una página por estación
troncal. El patrón de URL es `Metropolitano/<slug>/` (**en singular**, no
"Metropolitanos"). No existe un índice general navegable: se descubre cada página
desde la portada `https://portal.atu.gob.pe/QR/`.

| Columna | Descripción |
|---------|-------------|
| `estacion_slug` | Identificador en la URL |
| `estacion` | Nombre legible |
| `n_servicios` | Cuántos servicios cuelgan de esa estación |
| `servicios` | Lista de servicios detectados |

**Nota:** se detectaron 44 páginas de estación y 19 enlaces de servicio en total.

### `horarios_servicios.csv` / `horarios_corredores.csv` / `horario_linea1.csv`
Horario de primer y último bus por servicio y tipo de día. `min_ini` / `min_fin` son
minutos desde medianoche, para poder ordenar y comparar sin parsear texto.

### `paraderos_corredores.csv` — 1,111 paraderos
Orden de los paraderos por corredor y dirección, con origen y destino. Permite
reconstruir el recorrido.

### `frecuencias_l1_oficial.csv` — 3 filas (manual_verificado)

| tipo_dia | viajes_dia | min_pico | max_pico |
|----------|-------------|----------|----------|
| Lunes a Sábado | 510 | 3 | 4 |
| Sábado | 510 | 3 | 10 |
| Domingo | 292 | 6 | 12 |

Las dos primeras filas **no se contradicen**: la primera es la base de 510 viajes
diarios con la frecuencia de punta (3–4 min) de un día laborable; la segunda es el
detalle del sábado, que mantiene los 510 viajes pero con frecuencia de 3 a 10 min según
el horario. El domingo baja a 292 viajes y 6–12 min.

Fuente: [nota ATU sobre el aumento de viajes](https://www.gob.pe/institucion/atu/noticias/1281919-atu-linea-1-incrementa-el-numero-de-viajes-para-reducir-el-tiempo-de-espera-de-los-usuarios-en-las-estaciones)

**El sábado tiene 510 viajes igual que un día laborable.** Esto explica por qué el
sábado mueve lo mismo que el lunes en los datos de la L1 (ratio observado 1.01).

### `capacidad_vehiculos.csv` — 2 filas

| tipo | pasajeros | sentados | de_pie | longitud_m | confianza |
|------|-----------|----------|--------|------------|-----------|
| bus troncal articulado | 164 | 47 | 117 | 18.5 | `alta` |
| tren Línea 1 | 1,200 | — | — | — | `media` |

**El 1,200 del tren NO es un dato oficial.** El comunicado de la ATU (dic 2020) solo
publica que los trenes mueven 428–512 pasajeros con una ocupación del 36–43%. El 1,200 es
una **extrapolación nuestra** a partir de esa ocupación, marcada como
`metodo=derivado_del_comunicado` y `confianza=media`. El valor realmente oficial está en
`aforos_publicados.csv` (428–512) y en ningún lado debe usarse 1,200 como si fuera
medido.

Fuentes:
* Bus articulado, 164 pasajeros: [nota ATU](https://www.gob.pe/institucion/atu/noticias/895166-atu-nuevo-bus-articulado-del-metropolitano-podra-transportar-a-164-pasajeros)
* Tren L1 (derivado): [nota ATU](https://www.gob.pe/institucion/atu/noticias/320083-desde-el-lunes-14-de-diciembre-la-linea-1-del-metro-de-lima-y-callao-trasladara-el-doble-de-pasajeros-por-tren)

**Lo que NO está aquí:** la capacidad de los alimentadores (80 / 40 pasajeros). Se
buscó en el portal y en notas oficiales sin encontrar una fuente verificable, así que
**se dejó fuera** en vez de estimarla. Cualquier cifra de aforo de alimentador sería
inventada.

### `aforos_publicados.csv` — 4 filas

| indicador | valor | fecha | confianza |
|-----------|-------|------|-----------|
| ocupación actual | 17% | dic 2020 | alta |
| ocupación proyectada con flota Alstom | 36% | dic 2020 | alta |
| ocupación proyectada con flota Ansaldo | 43% | dic 2020 | alta |
| pasajeros por tren | 428–512 | dic 2020 | alta |

Fuente: [nota ATU sobre la ampliación de la L1](https://www.gob.pe/institucion/atu/noticias/320083-desde-el-lunes-14-de-diciembre-la-linea-1-del-metro-de-lima-y-callao-trasladara-el-doble-de-pasajeros-por-tren)

Es el **único aforo oficial publicado por la ATU** que se pudo localizar, y es un dato
puntual de 2020, no una serie. No hay nada equivalente para buses.

---

## Fuente no oficial

### `frecuencias_referencia.csv` — 19 servicios
Viene de [metrolima.info/metropolitano/rutas/](https://metrolima.info/metropolitano/rutas/),
un sitio **independiente**, no de la ATU. Los valores se cruzaron contra los valores
oficiales de la L1 y coinciden, pero eso no convierte al sitio en fuente oficial.

| Columna | Descripción |
|---------|-------------|
| `servicio` | Código (p. ej. `101`, `C`, `EX5`) |
| `nombre` | Nombre del servicio |
| `frecuencia_texto` | Texto original de la página |
| `min_pico` / `max_pico` | Minutos entre buses, o vacío |
| `n_paraderos` | Número de paraderos |
| `no_oficial` | Siempre `True` |
| `confianza` | Siempre `baja` |

**Limitación:** de los 19 servicios, solo **17 tienen frecuencia numérica**; `C` y
`EX5` no la tienen. El sitio **no cubre corredores**, así que las 12 rutas del
dataset de validaciones no salen aquí.

### `frecuencias_corredores_prensa.csv` — 5 filas (prensa/tesis 2023–2025)
Frecuencias numéricas de corredores. Criterio: **2023–2025**, preferir RPP o La
República; se aceptan Radio Nacional / Infobae si citan ATU/MTC; tesis UPC solo como
referencia contextual (`confianza=baja`).

| Columna | Descripción |
|---------|-------------|
| `corredor` / `servicio` | Color y código (p. ej. `Azul` / `SE08`) |
| `frecuencia_texto` | Texto literal de la nota |
| `min_pico` / `max_pico` | Minutos entre buses |
| `hora_ini` / `hora_fin` | Ventana operativa reportada |
| `n_paraderos_ida` / `n_paraderos_vuelta` | Paraderos por sentido |
| `anio` / `mes` / `medio` | Fecha y medio de la nota |
| `url` | URL exacta de la nota |
| `confianza` | `media` (prensa que cita autoridad, no tabla del portal) |
| `metodo` | `manual_verificado_prensa` |
| `nota` | Alcance y matices (p. ej. servicio nuevo vs. rutas del dataset) |

**Hallazgo documentado:** el *Servicio alimentador extraordinario 08* del Corredor
Azul (Lima ↔ San Martín de Porres) opera con **frecuencia ≈ 5 minutos**, lunes a
domingo de 05:00 a medianoche ([RPP, 31 ago 2025](https://rpp.pe/lima/actualidad/corredor-azul-inicia-este-domingo-marcha-blanca-de-nueva-ruta-que-unira-san-martin-de-porres-y-el-cercado-de-lima-noticia-1652874);
corroborado por [RPP, 3 set 2025](https://rpp.pe/lima/actualidad/comenzo-a-operar-nueva-ruta-del-corredor-azul-que-une-el-cercado-de-lima-y-smp-conoce-su-recorrido-y-paraderos-noticia-1653463)
y [Radio Nacional citando al ministro del MTC](https://www.radionacional.gob.pe/noticias/locales/corredor-azul-inauguran-nueva-ruta-que-une-smp-con-el-cercado-de-lima)).

**Cobertura parcial (sigue vigente como limitación de modelado):**

- Portal ATU / `metrolima.info` / TuRuta / Moovit / corredorrojo.pe: **no** entregan
  una tabla estática de headways para las 12 rutas del Excel.
- Sí hay cifras externas: **SE08 ≈ 5 min** (prensa 2025; no está en el Excel) y
  **404 ≈ 15 min** (tesis UPC 2023; sí es ruta del dataset, confianza baja).
- No apareció en RPP/La República 2023–2025 un intervalo usable para el Corredor
  Rojo ni para el resto de rutas Azul/Morado del Excel.
- Ver también `auditoria_apps_frecuencia.csv` y `docs/analisis.md`.
