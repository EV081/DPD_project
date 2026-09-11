# Diccionario de Datos — TransMilenio (UrbanSafe AI)

Fuente: Portal de Datos Abiertos de TransMilenio (Bogotá)
---

## 0. Conceptos clave del sistema

| Término | Qué es | Ejemplo en datos |
|---------|--------|------------------|
| **Troncal** | Corredor vial **exclusivo** para buses de TransMilenio (los autos no circulan). Cada troncal recorre una avenida principal de Bogotá. | `Autopista Norte`, `Calle 80`, `NQS`, `Caracas`, `Américas` |
| **Trazado** | **Segmento operativo** de una troncal, con letra A–Z y nombre propio. Una troncal puede tener varios trazados. | `TZ002` = Autopista Norte (Calle 80 → Terminal) |
| **Fase** | **Etapa constructiva histórica** de la infranstructura (no una jerarquía). Fase I ~2000, II ~2003, III ~2008, IV ~2016. | `FASE I`, `FASE IV` (en nuestros datos hay I–IV) |
| **Estación** | Punto de parada dentro de una troncal donde los usuarios entran/regresan. | `(02000) Portal Norte - Unicervantes` |
| **Portal** | Estación terminal al final de una troncal (mayor infraestructura). | 9 en el país: Portal Norte, Suba, 80, Américas, Tunal… |
| **ART / BIART** | Tipos de bus: **articulado** (~18 m) y **biarticulado** (~27 m, mayor capacidad). | — |
| **Ruta (servicio)** | Recorrido concreto de un bus, con código de letra+trayecto. | `B911`, `K23`, `GA503` |
| **Línea (agrupación)** | Grupo operativo de rutas que cubren una misma zona/troncal. NO es un bus específico. | `(33) Zona B AutoNorte` |

---

## 1. `dataset.csv` — Dataset procesado (principal para el modelo)

Creado por `process_transmilenio.py` agregando los ZIP diarios de Validación Troncal
por **(estación, fecha, hora, línea, tipo de día)**. Una fila = total de validaciones
de una línea en una estación en una hora concreta.

Cobertura actual: **69 días** (2026-07-01 → 2026-09-07), **97,065,085 validaciones**,
156 estaciones.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `Estacion` | str | Nombre de la estación con código Tullave, ej. `(02000) Portal Norte - Unicervantes`. |
| `Latitud` | float | Latitud de la estación (EPSG:4326). Vacío si la estación no está en el GeoJSON (~92% cobertura). |
| `Longitud` | float | Longitud de la estación (EPSG:4326). |
| `Ubicacion` | str | Dirección referencia (vías principales), ej. `CL 173`. |
| `Troncal` | str | Nombre de la troncal, ej. `Autopista Norte` (completada desde trazados). |
| `Fase` | str | Etapa constructiva, ej. `FASE I` (completada desde trazados). |
| `Cap_ART` | int | Capacidad de la estación (pasajeros) para buses **articulados**. En proceso de actualización por el operador. |
| `Cap_BIART` | int | Capacidad de la estación (pasajeros) para buses **biarticulados**. |
| `Fecha` | date | Fecha de la transacción, formato `YYYY-MM-DD`. |
| `Hora` | int | Hora de la transacción (0–23), sin padding. Ej. `3`, `15`. |
| `Linea` | str | Línea (agrupación operativa de rutas), ej. `(33) Zona B AutoNorte`. El número es el código, el texto describe zona+troncal. |
| `Tipo_Dia` | str | Clasificación binaria oficial: `Dia 1` = hábil (lun–sáb), `Dia 2` = domingo/no hábil. |
| `Validaciones` | int | N° de tarjetas validadas en esa celda (pasajeros que entran a la estación). |

---

## 2. Archivos crudos diarios (`diario/troncal/validacionTroncalYYYYMMDD.zip`)

Cada ZIP contiene un CSV (~600 MB) con **una fila por validación** (transacción Tullave).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `Estacion_Parada` | str | Estación donde se validó, ej. `(07503) SAN MATEO - C.C. UNISUR`. |
| `Fecha_Transaccion` | str | Fecha y hora `YYYY-MM-DD HH:MM:SS`. |
| `Day_Group_Type` | str | Tipo de día: `Dia 1` (hábil) / `Dia 2` (domingo). |
| `Linea` | str | **Línea** (agrupación de rutas), ej. `(30) Zona G NQS Sur`. Ver §0. |
| `Ruta` | str | Ruta/servicio concreto del bus (mayormente **vacío** en estos datos). |
| `Acceso_Estacion` | str | Punto de acceso, ej. `(03) Acceso Peatonal Norte`. |
| `Sistema` | str | `TRONCAL` (seleccionamos este). También existen ZONAL/BUSETAS en otros archivos. |
| `Operador` | str | Concesionario, ej. `(201) Trunk agency`. |
| `Dispositivo` | str | ID del equipo validador. |
| `Emisor` | str | Origen de la tarjeta, ej. `(3101000) Bogota Card(Citizen)`. |
| `Fase` | str | Fase de operación del servicio, ej. `Fase 3`. |
| `Hora_Pico_SN` | str | `Peak Time` (hora pico) / `Off' Pure Time` (valle). |
| `Numero_Tarjeta` | str | Hash SHA-256 de la tarjeta (seudonimizado, sin PII). |
| `Tipo_Tarjeta` | str | `tullave Básica`, etc. |
| `Tipo_Tarifa` | str | Tope/valor de tarifa, ej. `1,0`. |
| `Valor` | float | Tarifa en COP, ej. `3550.0`. |
| `Saldo_Previo_a_Transaccion` | float | Saldo de la tarjeta antes de validar (COP). |
| `Saldo_Despues_Transaccion` | float | Saldo de la tarjeta después de validar (COP). |
| `Fecha_Clearing` | date | Fecha del proceso de compensación monetaria. |
| `Nombre_Perfil` | str | Perfil del usuario, ej. `(001) Anonymous`. |
| `ID_Vehiculo` / `Tipo_Vehiculo` | str | Escaneados (mayormente vacíos). |

---

## 3. `geo/estaciones_troncales.geojson` — Estaciones (153 features = 147 operativas + duplicados/cierres temporales)

Estructura de la estación: portal/terminal, intercambios multi-troncal, intermedias y sencillas.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `objectid` / `num_est` | str/int | Código de estación Tullave (5 dígitos, ej. `07103`). PK. |
| `nom_est` | str | Nombre corto, ej. `AV. Chile`. |
| `cod_nodo` | int | Código de nodo de la red de transporte. |
| `latitud` / `longitud` | float | Coordenadas (EPSG:4326). |
| `ub_est` | str | **Referencia a vías principales** donde está la estación, ej. `KR 30 - CL 72` (Carrera 30 × Calle 72). Nomenclatura: KR=Carrera, CL/Calle, AV/Avenida, DG=Diagonal, TV=Transversal, AK=Avenida Carrera. |
| `id_trazado` | str | FK al trazado de la troncal, ej. `TZ008`. |
| `cap_art` | int | Capacidad de la estación (pasajeros) para buses **articulados**. |
| `cap_biart` | int | Capacidad de la estación (pasajeros) para buses **biarticulados**. |
| `tipo_esta` | int | **Tipo de estación** — 4 valores en datos (ver tabla abajo). |
| `num_vag` | int | N° de vagones (zonas de abordaje) de la estación. |
| `num_acc` | int | N° total de accesos. |
| `acc_esp` | int | Accesos desde espacio público (a nivel). |
| `acc_depr` | int | Accesos a través de **deprimidos** (pasos por debajo de la vía). |
| `acc_puent` | int | Accesos a través de **puentes** peatonales. |
| `long_est` / `ancho_est` / `area_est` | float | Dimensiones del andén (m, m, m²). |
| `esta_oper` | int | **Estado de operación** — en datos solo `1` = Existente. |
| `eta_oper` | int | **Etapa de operación** — 2 valores en datos (ver tabla abajo). |
| `observ` | str | Nota del operador (ej. "capacidades en actualización"). |

### Dominios para `tipo_esta` (definición oficial IDECA)

| Código | Significado | En nuestros datos |
|--------|-------------|-------------------|
| `1` | **Portal** (estación terminal de troncal) | 9 → Portal Norte, Suba, 80, El Dorado, Américas, Tunal, Usme, 20 de Julio, Sur |
| `2` | **Intermedia** (parada con 2 andenes de distinta troncal) | 9 |
| `3` | **Intercambio** (punto de transbordo entre troncales) | 6 → Ricaurte, Las Aguas, Universidades, AV. Jiménez |
| `4` | **Sencilla** (parada típica de una troncal) | 129 |
| `5` | Por definir | 0 (sin datos) |

### Dominios para `eta_oper` (definición oficial IDECA)

| Código | Significado | En nuestros datos |
|--------|-------------|-------------------|
| `1` | Operativa | 146 |
| `2` | Operativa con obras | 0 |
| `3` | **Cierre temporal por obras** | 7 → Tercer Milenio, Calle 45, Calle 19, Calle 63, Hospital, Patio Bonito, SENA |
| `4` | Cierre temporal - otros | 0 |

### Dominios para `esta_oper`

| Código | Significado | En nuestros datos |
|--------|-------------|-------------------|
| `1` | Existente (infraestructura construida y en operación) | 153 |
| (otro) | Proyectada | 0 |

---

## 4. `geo/trazados_troncales.geojson` — Troncales (22 features)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_trazado` | str | Código del trazado, ej. `TZ002`. PK. |
| `nom_traz` / `nom_tronc` | str | Nombre de la troncal, ej. `Autopista Norte`. |
| `le_troncal` | str | Letra de la troncal (A–Z), ej. `B`. |
| `fase_tronc` | str | **Fase constructiva**: `FASE I` (8 trazados), `FASE II` (6), `FASE III` (6), `FASE IV` (2). |
| `ori_traz` / `fin_traz` | str | Origen y destino del trazado (calles/portales). |
| `long_traz` | float | Longitud total del trazado (km). |
| `tipo_tra` | int | **Tipo de trazado** — 2 valores en datos (ver tabla abajo). |
| `esta_oper` / `eta_oper` | int | Estado: `1` = Existente / Operativa en todos. |
| `Shape__Length` | float | Longitud geométrica del trazado (m). |

### Dominios para `tipo_tra` (definición oficial IDECA)

| Código | Significado | En nuestros datos |
|--------|-------------|-------------------|
| `1` | **Exclusivo**: corredor solo para buses BRT | 17 trazados |
| `2` | **Mixto**: tramos donde los buses comparten carriles con vehículos particulares | 5 trazados |
| `3` | Sin definir | 0 |

---

## Notas

- **Cruce estaciones↔eventos:** el nombre de estación en eventos usa `(CÓDIGO) NOMBRE`.
  El proceso normaliza por código numérico (`int(num_est)`) para tolerar formatos con/sin espacio.
- **Troncal/Fase:** no están en estaciones (solo `id_trazado`); se completan cruzando con
  `trazados_troncales.geojson`.
- **Línea vs ruta:** el CSV crudo trae `Linea` (agrupación) con valores reales y `Ruta`
  (servicio concreto) casi siempre vacía. Por eso el dataset procesado agrega por `Linea`.
- **Unidades:** tarifas y saldos en pesos colombianos (COP).
- **Privacidad:** `Numero_Tarjeta` es un hash SHA-256, no contiene PII.
- **Estado:** 7 estaciones con `eta_oper=3` (cierre temporal por obras) explican ausencias
  de datos en ese período; considerar al interpretar series temporales.