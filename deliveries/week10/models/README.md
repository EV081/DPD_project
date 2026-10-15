# Modelos serializados — UrbanSafe AI (Issue #19)

**Autor:** Juan David Velo Poma — Data Scientist · **Versión:** ver `manifest.json`

Artefactos del prototipo de la semana 10: un modelo operativo por sistema (Metro L1, Metropolitano
troncal, corredores complementarios y alimentadores), con su manifiesto (versión, hiperparámetros,
métricas contra baselines y sha256) y una verificación de recarga reproducible.

> La evaluación que respalda estas métricas está en `deliveries/week09/code/model/`
> (`evaluar_v2.py` + `Evaluacion_Modelos_v2.ipynb`): validación 15–31 oct 2025 para elegir el
> modelo y **test 1 nov – 31 dic 2025 (61 días)** para reportar. Una copia de las tablas está en
> `evaluacion/<sistema>/`.

## 1. Qué hay aquí

```
models/
├── manifest.json            ← versión, commit, sha256 de datos y de cada artefacto, entorno, resumen de métricas
├── verify_report.{json,md}  ← resultado de la última verificación de recarga
├── calendario_eventos.json  ← feriados 2025–2026 y paros de transportistas 2025 (con fuente)
├── regla_u.json             ← regla de recomendación (abordar / esperar / cambiar de paradero)
├── eta_config.json          ← definición del ETA (headway × factor por clase de aforo)
├── evaluacion/<sistema>/    ← métricas de test vs baselines (copiadas de week09)
└── <sistema>/
    ├── model_card.json              ← modelo principal, hiperparámetros, métricas, criterios RNF/AC
    ├── lightgbm.txt + _meta.json    ← LightGBM global (formato nativo), features y orden de unidades
    ├── crowding_config.json         ← umbrales p60/p90 por franja, α, k, capacidad, headways, orden upstream
    ├── conformal.json               ← cuantiles por hora para la banda del 80 % del modelo principal
    ├── conformal_ligero.json        ← ídem para el modo ligero (LightGBM)
    ├── aforo_histgb.joblib + _meta  ← clasificador directo de aforo (respaldo sin pronóstico)
    ├── anomalias.json               ← detector por residuos (z robusto) + referencia mediana/MAD
    ├── isolation_forest.joblib      ← detector de week08 (comparación)
    ├── referencia_contexto.csv      ← 35 días de contexto usados en la verificación
    ├── referencia_salida.csv        ← salida esperada para el día de referencia (2026-01-01), modo principal
    ├── referencia_salida_ligero.csv ← ídem, modo ligero
    └── referencia_artefactos.npz    ← entradas/salidas de referencia de cada artefacto
```

Los modelos fundacionales (Chronos-2, Chronos-Bolt) **no** se versionan en git (478 MB y 191 MB):
`model_card.json` fija el repositorio de Hugging Face y la **revisión exacta** (`revision`), y la
verificación compara su salida contra `referencia_salida.csv`.

## 2. Uso desde el backend o un batch diario

```python
import sys
sys.path.insert(0, "deliveries/week10/code/model")
from inferencia import ModeloSistema

m = ModeloSistema.cargar("metro_l1")          # valida sha256 contra manifest.json
# contexto: DataFrame con índice horario (Fecha_Hora) y una columna por unidad,
# al menos 28 días completos hasta el día anterior a las 23:00 (p. ej. desde la vista demanda_fiable)
salida = m.pronosticar(contexto, "2026-01-01")
```

`salida` trae, por unidad y hora:

- `validaciones_pron` y la banda del 80 % (`banda80_lo`, `banda80_hi`);
- `crowding_index` y `aforo` (Asientos / De_pie / Saturado);
- `eta_min` y `eta2_min` (las dos próximas unidades, RF-02);
- `recomendacion` y el `modelo` usado.

Si el modelo principal falla, la inferencia degrada a `media_4sem` (espíritu RF-05). Para alertas se
usa `m.anomalia_dia(contexto, dia, reales)`.

**Modos de inferencia:**

| Modo | Modelo | Latencia medida | Requiere |
| :--- | :--- | :--- | :--- |
| `modo="principal"` (por defecto) | Ganador de validación (ensemble con Chronos-2 en L1, troncal y corredores; LightGBM en alimentadores) | ~33 s en la primera llamada (carga de Chronos-2), ~2 s después | torch + chronos-forecasting |
| `modo="ligero"` | LightGBM | ~0.01 s | solo lightgbm |

El modo ligero tiene precisión **estadísticamente equivalente** a la del principal (Diebold-Mariano
p = 0.28–0.63; ver `model_card.json → pronostico.modo_ligero`). Para cumplir AC-04 (P95 ≤ 2 s) hay
dos opciones:

- servir en modo ligero;
- correr el modo principal en un **batch diario** que guarde el resultado en la tabla `prediccion` de
  PostgreSQL (esquema de Elmer), de modo que la API solo consulte.

## 3. Regenerar y verificar

```bash
pip install -r deliveries/week10/requirements-models.txt
# 1) (opcional) evaluación completa ≈ 1 h en CPU
.venv/Scripts/python deliveries/week09/code/model/evaluar_v2.py
# 2) serializar con todo 2025 (lee results_v2 de week10 o week09)
.venv/Scripts/python deliveries/week10/code/model/serializar_modelos.py
# 3) verificación de recarga (sha256 + recarga + re-inferencia)
.venv/Scripts/python deliveries/week10/code/model/verificar_modelos.py
# 4) pruebas (no requieren PostgreSQL)
cd deliveries/week10/code && python -m pytest tests/test_models.py -q
```

Los `.joblib` son pickles: solo se cargan si su sha256 coincide con `manifest.json`, y con la
misma versión de scikit-learn registrada en el manifiesto.

## 4. Resumen

| Sistema | Modelo principal | WMAPE test | WMAPE modo ligero | Mejor baseline (WMAPE) | F1-weighted aforo | Acuerdo regla U | RNF-01 | AC-02 | AC-03 |
| :--- | :--- | ---: | ---: | :--- | ---: | ---: | :---: | :---: | :---: |
| Metro L1 | ensemble (lightgbm + chronos2 + mstl) | 0.102 | 0.100 | media_4sem (0.126) | 0.919 | 96.9 % | ✅ | ✅ | ✅ |
| Troncal | ensemble (lightgbm + chronos2 + mstl) | 0.123 | 0.115 | media_4sem (0.160) | 0.907 | 97.8 % | ✅ | ✅ | ✅ |
| Corredores | ensemble (lightgbm + chronos2 + chronos_bolt) | 0.120 | 0.113 | media_4sem (0.167) | 0.927 | 97.6 % | ✅ | ✅ | ✅ |
| Alimentadores | lightgbm | 0.405 | 0.405 | media_4sem (0.472) | 0.842 | 97.0 % | ✅ | ❌ | ✅ |

Versión **1.0.0** · código en el commit `68fa26b` (sin cambios pendientes: sí) · datos sha256 `694c595f67f6…` (12,344,159 filas) · verificación de recarga: **OK** (197/197 checks, ver `verify_report.md`).

AC-03 se cumple, pero también lo cumple «siempre abordar» (90–96 %). Por eso reportamos además la balanced accuracy (`evaluacion/<sistema>/regla_u_test.csv`).

## 5. Limitaciones

- Las validaciones son abordajes, no ocupación a bordo: el aforo es un índice de presión de abordaje.
- Los umbrales p60/p90 por franja hacen que "Saturado" sea relativo a cada franja horaria
  (ver `evaluacion/<sistema>/aforo_sensibilidad_umbrales.csv`).
- Sin GPS/AVL no hay llegadas reales: el error de ETA reportado es el inducido por el modelo.
- Un solo año de historia (2025); los paros no se anticipan, se detectan después.
- El efecto del tráfico sobre el ETA **no está entrenado** (ver §6).

## 6. Ajuste en vivo del ETA (TomTom)

Tres capas desacopladas; la API nunca llama a TomTom:

| Capa | Frecuencia | Qué hace |
| :--- | :--- | :--- |
| A. Demanda | 1 vez al día | `python -m pipeline.run predict` → `prediccion` (demanda, banda 80 %, aforo, ETA base, regla U) |
| B. Tráfico | cada 5 min | `python -m pipeline.run loop` → `trafico_en_vivo` (último) y `trafico_historico` (serie) |
| C. Ajuste | por consulta | `ajuste_vivo.ajustar_en_vivo()`: `eta = eta_base × factor_trafico`, recalcula la regla U |

- `factor_trafico = clip(velocidad_libre / velocidad_actual, 1.0, 1.5)`, solo en vía mixta
  (`corredor`, `alimentador`; ver `mapeo_segmentos.json`). Metro y troncal no se ajustan.
- Antigüedad del snapshot: ≤ 10 min `en_vivo`; 10–30 min `reciente` (peso 0.5);
  > 30 min, sin dato o fuente `fallback` → `historico` (sin ajuste, RF-05).
- **Hipótesis no entrenada** (`ajuste_vivo_config.json`): no hay histórico TomTom alineado con 2025
  ni AVL. El ETA *incorpora* el tráfico actual; no se afirma que lo *mejore*. El mapeo
  segmento→sistema es un supuesto geográfico a validar.
- `prediccion` guarda la clase de la hora; `ajustar_en_vivo` recibe `aforo_siguiente` opcional
  (si falta, la regla U asume la misma clase para h+1).

### Validación con feedback (sin reentrenamiento automático)

`feedback_usuario` registra `t_consulta`, `t_aborde` ("Ya abordé"), ETA/aforo mostrados, modo de
datos y `entorno` (`demo`|`prod`). Espera real = `t_aborde − t_consulta`. El aforo percibido es
opcional y se pregunta con probabilidad `FEEDBACK_AFORO_PROB` (demo 1.0, prod 0.2–0.33).
Métrica: error absoluto mediano del ETA por `modo_datos`, con n ≥ ~30 eventos por sistema;
los registros `demo` se excluyen. Con `aforo_percibido` se revisan a mano los umbrales p60/p90.
