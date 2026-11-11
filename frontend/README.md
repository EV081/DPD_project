# UrbanSafe · Frontend web (Next.js)

Aplicación web responsive (móvil, tablet y escritorio) que consume la API Flask de `../backend`.

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL (por defecto, la API de Render)
npm install
npm run dev                  # http://localhost:3000
npm run build && npm start   # producción
```

Para usar el backend local: `NEXT_PUBLIC_API_URL=http://localhost:5000/api`.

Rutas: `/login`, `/register`, `/map`, `/search`, `/destinations`, `/station/[id]`, `/account`.

## UI y experiencia de uso

- Mantine: campos con etiquetas y ayuda, contraseñas con control de visibilidad, diálogos con foco contenido y restaurado, avisos, selectores y pestañas del panel.
- Material UI: navegación inferior móvil con enlaces de Next, etiquetas visibles y estado activo.
- Ambos temas se sincronizan desde `ThemeContext`; `UIProvider` centraliza la configuración. El orden de capas CSS es `theme, base, mantine, mui, components, utilities`; no añadir un segundo reset global.
- `DataTable<T>` usa TanStack Table v8: orden, búsqueda local, paginación y CSV de todas las filas filtradas y ordenadas. El catálogo permite alternar tarjetas y tabla. Las tablas de gráficos y de procesos usan el mismo componente.
- Recharts: gráficos del panel y de ocupación horaria en simulación, con tabla alternativa y movimiento reducido.
- React Leaflet v5 gestiona marcadores, popups y rutas. MapLibre dibuja la base vectorial OpenFreeMap clara/oscura. Si falla al cargar o no hay WebGL, se usa OpenStreetMap ráster. Requiere acceso de red a los proveedores cartográficos; no requiere una clave nueva.
- Los minimapas mantienen atribución de OpenStreetMap y muestran los nombres como texto de React.

Comprobaciones: `npm run lint`, `npm test`, `npm run build`. En entornos que bloquean los puertos internos de Turbopack se puede verificar con `npx next build --webpack`.
