// Pantallas reservadas a la cuenta administradora (la API también lo exige: esto solo decide qué se muestra).
export const ADMIN_ROUTES = ['/simulacion', '/dashboard'] as const;

export const isAdminRoute = (pathname: string) =>
  ADMIN_ROUTES.some((ruta) => pathname === ruta || pathname.startsWith(`${ruta}/`));

/** Valida el parámetro ?continuar=… del login: solo rutas de administración conocidas (nunca una URL arbitraria). */
export const destinoAdmin = (valor: string | null): string | null => {
  const ruta = valor ? `/${valor.replace(/^\//, '')}` : null;
  return ruta && (ADMIN_ROUTES as readonly string[]).includes(ruta) ? ruta : null;
};
