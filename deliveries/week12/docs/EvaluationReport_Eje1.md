# Evaluation Report — UrbanSafe AI (Week 12)

> **Sección: Modelo de demanda y aforo** (responsable: Juan David Velo Poma, Data Scientist).
> Las secciones de producto, usabilidad y rutas seguras se integran en este mismo documento.

**Código evaluado:** repositorio `Alessandromg18/Backend_UrbanSafe`, rama `feat/aforo-od-ocupacion`,
modelos **v1.3.0** (`models/manifest.json`). La documentación técnica completa está en
`docs/MODELO_OCUPACION.md` del backend.

## 1. Qué se evalúa

La app informa, para cada estación o paradero y cada hora:
- la **ocupación del vehículo**: pasajeros a bordo / capacidad, con clase *Asientos*, *De pie* o
  *Saturado*;
- la **espera estimada**;
- una **recomendación**: abordar, esperar el siguiente o cambiar de paradero.

Se obtiene en dos etapas:

1. **Pronóstico de demanda (ML):** LightGBM pronostica las **subidas** horarias (validaciones de
   tarjeta ATU) de cada estación o ruta. En alimentadores, de cada ruta y sentido.
2. **Ocupación a bordo (modelo de transporte):** la ATU solo entrega subidas, sin bajadas. A partir
   de las subidas pronosticadas se reconstruye la **matriz origen-destino** con los métodos de
   Ortúzar y Willumsen (*Modelos de Transporte*, 2008). Las bajadas se estiman por **viaje de
   retorno**: quien baja en *j* por la mañana vuelve a subir en *j* por la tarde. Las matrices se
   balancean con **Furness** (gravedad doblemente acotada; acotada a orígenes en corredores). Con
   eso se calcula la carga por tramo y sentido y, con la oferta publicada, los pasajeros por
   vehículo.

La versión anterior (v1) usaba un índice de "presión de subida" con umbrales relativos por franja
horaria. No medía la ocupación real del vehículo.

## 2. Estrategia de validación

| Elemento | Definición |
|---|---|
| Datos | Validaciones ATU 2025, horarias: Metro L1 (26 estaciones), Metropolitano troncal (45), corredores (12 rutas, ~900 paraderos), alimentadores (23 rutas) |
| Partición temporal | Entrenamiento ene–sep · early stopping 01–14 oct · **validación 15–31 oct** · **test 1 nov – 31 dic** (61 días) |
| Protocolo | *Rolling-origin*: para cada día de test el modelo **solo ve días anteriores** y se reentrena cada 7 días |
| Verdad para el aforo | La misma cadena O-D aplicada a las subidas **observadas** (por paradero en corredores y por sentido en alimentadores). El error medido incluye el pronóstico y el reparto a paraderos |
| Validación del modelo O-D | Sin datos de bajadas reales: (a) prueba sintética de recuperación, (b) sensibilidad a β, (c) contraste con cifras públicas |
| Selección de modelos | Siempre en validación, con reglas fijadas antes de mirar el test |

**Corrección de fuga de información.** Una versión intermedia (1.1.x) evaluaba con el modelo
serializado, que había sido entrenado con todo 2025, incluido el test. Las métricas resultaban
optimistas (Metro F1-macro 0,92 en vez de 0,86). En v1.2.0 toda la evaluación es fuera de muestra;
aquí solo se reportan esas cifras.

## 3. Métricas

| Métrica | Uso | Umbral |
|---|---|---|
| **WMAPE** = Σ\|ŷ−y\| / Σy | Error del pronóstico de demanda y de la carga a bordo | — |
| **MAE** (pasajeros por vehículo) | Error de carga en unidades interpretables | — |
| **Accuracy** y **F1-macro** de la clase de aforo | Calidad de lo que ve el usuario | RNF-01: accuracy ≥ 0,75 y F1-macro ≥ 0,72 |
| F1-weighted, balanced accuracy | Complementarias (clases desbalanceadas) | — |
| Cobertura de la banda del 80 % | Calibración de la incertidumbre | ≈ 0,80 |
| P95 de latencia de la API | Experiencia en la app | AC-04: ≤ 2 s |

## 4. Resultados

### 4.1 Pronóstico de demanda (test, fuera de muestra)

| Sistema | LightGBM (producción) | Mejor baseline | Ensemble con Chronos |
|---|---:|---:|---:|
| Metro L1 | **WMAPE 0,100** | media_4sem 0,126 | 0,102 |
| Troncal | **0,115** | media_4sem 0,160 | 0,123 |
| Corredores | **0,113** | media_4sem 0,167 | 0,120 |
| Alimentadores (ruta × sentido, v1.2.0) | **0,483** | modelo por ruta repartido 0,545 | — |

LightGBM es el modelo de producción por tres razones:
- iguala o supera al ensemble con Chronos-2 en test;
- corre en milisegundos;
- no necesita torch, que no entra en la memoria del servidor.

### 4.2 Aforo que ve el usuario (test, fuera de muestra)

| Sistema (nivel) | Modelo | Accuracy | F1-macro | WMAPE de la carga | MAE (pas./vehículo) | RNF-01 |
|---|---|---:|---:|---:|---:|:---:|
| Metro L1 (estación × sentido) | **LightGBM + O-D** | **0,931** | **0,856** | **0,089** | 40,6 | ✅ |
| | media_4sem + O-D | 0,918 | 0,830 | 0,127 | 58,2 | |
| Troncal (estación × sentido) | **LightGBM + O-D** | **0,931** | **0,926** | **0,095** | 6,6 | ✅ |
| | media_4sem + O-D | 0,908 | 0,899 | 0,184 | 12,7 | |
| Corredores (paradero × sentido) | **LightGBM + O-D** | **0,919** | 0,655 | **0,196** | 3,9 | ❌ (F1) |
| | media_4sem + O-D | 0,891 | 0,555 | 0,298 | 5,9 | |
| Alimentadores (ruta × sentido) | **LightGBM por sentido** | **0,857** | 0,539 | **0,525** | 5,3 | ❌ (F1) |
| | LightGBM por ruta (v1.1) | 0,842 | 0,480 | 0,573 | 5,8 | |
| | media_4sem | 0,821 | 0,467 | 0,643 | 6,5 | |

- LightGBM supera al baseline en los cuatro sistemas.
- En corredores y alimentadores la accuracy cumple, pero el F1-macro no. "Saturado" es rara en
  buses (1,5 % y 2,7 % de las horas de test) y el F1-macro pesa igual a las tres clases.
- **Latencia:** pronóstico más O-D en unos 0,02 s por día y sistema; P95 de la API en caliente < 2 s
  (AC-04, verificado en `tests/test_api.py`).
- **Incertidumbre:** banda del 80 % en alimentadores con cobertura empírica de 81,2 % en los días no
  usados para calibrar.

### 4.3 Validación del modelo origen-destino (Metro L1)

| Prueba | Resultado |
|---|---|
| Algoritmo de Furness | Reproduce la Tabla 5.7 de Ortúzar y Willumsen (test automático) |
| Recuperación sintética (40 días, supuestos violados a propósito) | Contra el baseline de bajadas uniformes: error de bajadas 0,26 frente a 0,63; error de carga 0,24 frente a 0,33; F1-macro de clase 0,71 frente a 0,55 |
| Simetría del viaje de retorno | La matriz diaria estimada es 93,5 % simétrica (T_ij ≈ T_ji) |
| Sensibilidad a β | β = 0 (máxima entropía, §12.4.4) minimiza la asimetría; con β entre 0 y 0,05, la carga pico varía −16 % |
| Longitud de la línea | 34,7 km (Ositrán: 34 km; Grau en el km 22,0 frente a 22,1 del tramo 1) |
| Tramos críticos en punta | 7:00: El Ángel → Grau y Ayacucho → Cabitos (hacia el centro); 18:00: Grau → El Ángel (regreso a SJL), 1007 pasajeros por tren, 84 % |
| Demanda | 600 mil subidas por día laborable (Ositrán 2024: 191 millones al año) |

### 4.4 Comparación con el índice v1 (subidas observadas, test)

| Sistema | "Saturado" en punta: v1 → v2 | "Saturado" en valle: v1 → v2 |
|---|---:|---:|
| Metro L1 | 14 % → **23 %** | 18 % → **4 %** |
| Troncal | 12 % → **35 %** | 13 % → **18 %** |
| Corredores | 11 % → **9 %** | 10 % → **0,2 %** |
| Alimentadores | 6 % → **12 %** | 7 % → **1 %** |

El v1 marcaba "Saturado" por percentiles **dentro de cada franja**, así que el valle salía igual o
más saturado que la punta. La v2 mide la ocupación contra la capacidad del vehículo y concentra la
saturación en la punta.

### 4.5 Recomendación (abordar / esperar el siguiente / cambiar de paradero)

**Antes.** La regla v1 comparaba la hora actual con la siguiente. Con un vehículo cada 1,5–3
minutos, el siguiente cae en la misma hora, así que decía "abordar" en el 95–99 % de las horas.

**Ahora (v1.3.0).** Cada opción se valora por **costo generalizado** en minutos equivalentes
(Ortúzar y Willumsen, ec. 10.18):

    2 · caminata + 2 · espera + multiplicador de hacinamiento · tiempo a bordo

El multiplicador de hacinamiento es el de Whelan y Crockett: sentado 1,00 → 1,63 y de pie
1,53 → 2,04. Con eso:

- **"Esperar el siguiente"** si P(el vehículo que te toca llega lleno) ≥ 0,5. Esa probabilidad
  modela la irregularidad del servicio: los buses atrasados llegan más llenos.
- **"Cambiar de paradero"** si subir en un paradero anterior (≤ 600 m) ahorra ≥ 3 minutos
  equivalentes.
- En la búsqueda por destino, las rutas se **ordenan por costo generalizado** y se descartan los
  paraderos en sentido contrario.

| Medición | Resultado |
|---|---|
| 40 viajes de corredores en hora punta | La opción vieja (menor caminata) estaba **en sentido contrario en el 70 %**; la nueva nunca. En 9 viajes recomienda otra ruta o paradero (ahorro mediano: 6 min equivalentes) |
| "Esperar el siguiente" en hora punta (observado) | Troncal 15 %, alimentadores 6 %, corredores 0,2 %, Metro 0 % (los trenes van en promedio al 75–85 %) |
| AC-03 (recomendación pronosticada = observada, fuera de muestra) | Metro 99,8 %, troncal 96,8 %, corredores 99,1 %, alimentadores 97,7 %. Solo en el troncal supera claramente a "siempre abordar" (89,4 %; balanced accuracy 0,91) |

## 5. Caso de estudio

**Usuaria:** trabaja en Gamarra y vive en Villa El Salvador. Es miércoles 4 de noviembre de 2026,
18:00, y abre la app en la estación Gamarra con destino Villa El Salvador.

1. La app toma su ubicación, ella elige el destino y `match-trip` propone la Línea 1 de Gamarra a
   Villa El Salvador.
2. La app pide `GET /api/predictions/estacion/<Gamarra>?hacia_id=<Villa El Salvador>`.
   - Como no hay datos ATU de 2026, el backend usa el **día homólogo** (miércoles 5-11-2025) y lo
     declara en la respuesta.
   - El destino define el **sentido**: hacia Villa El Salvador.
3. Respuesta real de la API:

   | Sentido | Hora | Clase | Ocupación | A bordo | Espera | Recomendación |
   |---|---|---|---:|---:|---:|---|
   | hacia Villa El Salvador | 18:00 | De pie | 48 % | ≈ 576 | 1,5 min | Abordar |
   | hacia Bayóvar (otro sentido) | 18:00 | **Saturado** | 85 % | ≈ 1014 | 1,5 min | Abordar (a las 19:00 sigue saturado) |

4. **Lectura:** en su sentido el tren va de pie pero sin saturar. El sentido contrario, que es el
   regreso a San Juan de Lurigancho, va saturado. La v1 no distinguía sentidos y le habría mostrado
   el mismo valor para ambos.

Otros ejemplos de la misma fecha:
- **Troncal:** en Naranjal a las 7:00 hacia el centro, ocupación de 110 % ("Saturado") con
  recomendación **esperar el siguiente**, porque la hora siguiente es menos crítica.
- **Corredor Rojo 201:** el paradero Aviación hacia Venezuela a las 7:00 sale "De pie", con 74 %
  (unos 59 a bordo) y espera de 1,1 min.

## 6. Limitaciones

- **Sin datos de bajadas ni GPS:** la matriz O-D se valida de forma sintética, por consistencia y
  contra cifras públicas, no contra viajes reales. El reporte de los usuarios (aforo percibido)
  permitirá recalibrar.
- **Oferta de buses derivada:** las flotas publicadas por corredor se reparten con el método del
  punto de carga máxima (Ceder); el troncal usa 117 buses/h en punta, un dato de 2013. La ocupación
  escala con 1/frecuencia.
- **Datos 2025:** las fechas de 2026 usan el día homólogo de 2025; no capturan cambios posteriores
  (por ejemplo, la flota o las aperturas de la ampliación norte).
- **Alimentadores y corredores no cumplen el F1-macro de RNF-01.** En alimentadores el error está en
  el reparto horario de la demanda, que varía mucho de un día a otro. Pasos siguientes:
  - covariables de llegadas a la estación de integración (estimadas por la matriz O-D del troncal);
  - pronóstico por franjas de 2–3 horas.
- Promedios horarios: no se modela la punta de 15 minutos.

## 7. Reproducibilidad

```bash
# backend (Alessandromg18/Backend_UrbanSafe, rama feat/aforo-od-ocupacion)
pip install -r requirements.txt pytest shapely
python -m pytest tests                               # 44 tests: Furness, calendario, API, recomendación, latencia, recarga
python scripts/evaluar_ocupacion.py                  # sección 4.2 (fuera de muestra)
python scripts/evaluar_od_metro_l1.py                # sección 4.3
python scripts/entrenar_alimentador_sentido.py --datos <DPD_project>/deliveries/week10/data_processed/clean
python scripts/serializar_modelos.py 1.3.0 "<cambios>"   # manifiesto sha256 + salidas de referencia
```

Los datos limpios de entrada vienen del pipeline de `deliveries/week10` de este repositorio.
