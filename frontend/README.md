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
