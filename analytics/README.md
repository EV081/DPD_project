# Laboratorio de indicadores de UrbanSafe AI

Este módulo genera un escenario de **600 usuarios ficticios, con una sesión sintética por usuario**, y alimenta un tablero separado del panel operacional. Cada usuario tiene un `usuario_id` como `USR-SIM-0001`; no se generan nombres, correos ni datos personales. Su propósito es demostrar filtros, métricas y gráficos. Los ETA, aforos, tiempos de respuesta y fallos se calculan con supuestos del generador: **no son salidas del modelo LightGBM ni mediciones de la API desplegada**.

## Qué contiene

| Archivo | Uso |
|---|---|
| `generar_simulacion.py` | Generador determinista. Lee estaciones y rutas del catálogo actual del proyecto. |
| `output/urbansafe_simulacion_600.csv` | Base tabular para análisis en Python, Excel o Power BI. |
| `output/resumen_simulacion_600.json` | Controles rápidos del escenario generado. |
| `../frontend/public/simulacion/urbansafe_simulacion_600.json` | Fuente que consume el tablero web. |
| `../frontend/public/tablero-simulacion.html` | Tablero interactivo autónomo. |
| `test_simulacion.py` | Pruebas de reproducibilidad, catálogo, embudo y ausencia de datos personales. |

## Cómo regenerarlo

Desde la raíz del proyecto:

```powershell
python analytics\generar_simulacion.py
python -m unittest analytics.test_simulacion -v
```

Para cambiar el tamaño o el periodo:

```powershell
python analytics\generar_simulacion.py --registros 1000 --hasta 2026-12-15 --semilla 20261215
```

El tablero espera el nombre `urbansafe_simulacion_600.json`. Si se cambia el tamaño, el archivo mantiene ese nombre para no romper el enlace; la cantidad real se lee del contenido.

## Cómo verlo

1. Ejecutar el frontend de UrbanSafe.
2. Abrir `/tablero-simulacion.html` o usar el enlace «Laboratorio con datos simulados» del panel administrativo.
3. Filtrar por sistema y fechas. Todos los indicadores y gráficos se recalculan en el navegador.
4. «Cargar otro JSON» permite comparar un escenario generado con el mismo esquema sin reemplazar archivos.

## Variables

Cada fila representa la sesión de un usuario ficticio. `usuario_id` identifica al usuario y `sesion_id` identifica la sesión. En la muestra incluida hay 600 usuarios distintos y 600 sesiones; si otro escenario repite un usuario en varias sesiones, el tablero cuenta ese usuario una sola vez dentro del filtro. Los archivos anteriores sin `usuario_id` siguen admitiéndose, pero muestran el conteo de usuarios como no disponible. Incluye:

- momento, sistema, estación y ruta tomados de los catálogos del proyecto;
- avance por el embudo: consulta, recomendación vista, abordaje y feedback;
- ETA predicho y observado, error absoluto, aforo predicho y observado;
- consulta de ruta segura y reporte de seguridad ficticio;
- latencia, respuesta correcta, uso de caché y fallback histórico.

No contiene nombres, correos, teléfonos, coordenadas ni identificadores reales.

## Lectura de los indicadores

- **Conversión a abordaje:** abordajes simulados / consultas simuladas.
- **MAE ETA:** promedio del valor absoluto entre espera observada y predicha, solo donde hay abordaje simulado.
- **Sesgo ETA:** promedio de `observado − predicho`. Positivo significa que la espera observada fue mayor.
- **Acierto de aforo en el escenario:** coincidencia entre Asientos, De pie o Saturado hipotéticos. Se usan los mismos nombres que la aplicación, pero los umbrales de esta simulación son ilustrativos.
- **Disponibilidad API:** respuestas correctas / consultas del escenario.
- **Latencia p95:** el 95 % de respuestas simuladas queda por debajo de ese tiempo.
- **Fallback histórico:** sesiones que usan una estimación histórica en vez de tráfico en vivo.

## Límites

El escenario no valida demanda, precisión del LightGBM, seguridad, ventas ni desempeño técnico real. La aplicación aún no recoge una puntuación de satisfacción, por eso el archivo no la incluye. Las probabilidades son supuestos de demostración declarados en el generador. Para decisiones del producto se debe usar el panel operacional autenticado, telemetría consentida y observaciones reales evaluadas por el equipo.
