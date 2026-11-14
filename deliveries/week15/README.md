# Entrega 2 · Semana 15 — UrbanSafe AI (DS-3022, UTEC 2026-II)

Entrega final reproducible del producto de datos. El README completo del proyecto (instalación,
ejecución, dependencias, datos, modelos, despliegue) está en el [README de la raíz](../../README.md).

| Entregable de la guía | Archivo |
| :--- | :--- |
| Informe final (+ fuente editable) | [`FinalReport.pdf`](FinalReport.pdf) · [`FinalReport.tex`](FinalReport.tex) |
| Presentación final | `PresentationFinal.pptx` / `PresentationFinal.pdf` (ver estado abajo) |
| Video demo (5–7 min) | guion en [`DemoVideo.md`](DemoVideo.md); **enlace pendiente** |
| Data Product Canvas | [`DataProductCanvas.pdf`](DataProductCanvas.pdf) (actualizado sobre la plantilla A0 del curso) |
| Requerimientos finales | [`Requirements.md`](Requirements.md) (incluye estado de cumplimiento, §11) |
| Arquitectura y flujo | [`diagrams/architecture.png`](diagrams/architecture.png) · [`-dark.png`](diagrams/architecture-dark.png) · [`.html`](diagrams/architecture.html) |
| Evaluación, baselines y casos de estudio | Informe §7; detalle en `../week12/docs/EvaluationReport_Eje1.md` y `Model_Eje2.md` |
| Página del proyecto | [`project_page/index.html`](project_page/index.html) |
| Contribución del equipo y reflexión | Informe §10–§11 (**borrador: el equipo debe completarlo**) |

## Enlaces
* Web (Vercel): <https://dpd-project.vercel.app>
* API (Render): <https://urbansafe-api.onrender.com/api/health> · Swagger en `/apidocs`
* Base de datos: Supabase (PostgreSQL). Sus credenciales **no** se versionan.
* Repositorio: <https://github.com/EV081/DPD_project>

> El plan gratuito de Render duerme el servicio: el primer pedido tarda ~50 s. Abrir antes `/api/health`.

## Reproducir
```bash
# Todo local con Docker (Postgres + API :5000 + web :3002)
cp .env.example .env && docker compose up --build   # desde la raíz del repo

# Pruebas del backend (217)
docker compose --profile test up -d db-test && cd backend && pip install pytest && python -m pytest

# Verificación del frontend
cd frontend && npm ci && npx tsc --noEmit && npx next build
```
Datos, modelos, pipeline y notebooks: tabla 5.D del [README raíz](../../README.md).

## Compilar el informe
```bash
tectonic FinalReport.tex      # o: xelatex FinalReport.tex (dos veces)
```

## Regenerar el diagrama
Hecho con la skill [`stack-diagram`](https://github.com/caru-ini/stack-diagram)
(`npx skills add caru-ini/stack-diagram`); la fuente es `diagrams/architecture.html`.

## Limitaciones conocidas y problemas frecuentes
* Corredores y alimentadores no cumplen F1-macro ≥ 0,72 (RNF-01); sin bajadas reales ni GPS; fechas
  de 2026 usan el día homólogo de 2025; denuncias ≠ delito (subregistro y sesgo). Ver informe §8.
* Sin `DATABASE_URL` la API usa SQLite (solo desarrollo; no soporta las tablas particionadas del Eje 2).
* Si TomTom o LocationIQ no están configurados, la API degrada a datos históricos / sin autocompletado.
