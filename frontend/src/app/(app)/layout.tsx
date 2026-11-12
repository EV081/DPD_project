'use client';

import BottomNavigation from '@mui/material/BottomNavigation';
import BottomNavigationAction from '@mui/material/BottomNavigationAction';
import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Map, Search, Navigation, User, ChartColumn, LayoutDashboard, ShieldAlert } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Logo } from '@/components/Logo';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Spinner } from '@/components/Spinner';
import { isAdminRoute } from '@/lib/access';

const NAV: { href: string; label: string; icon: typeof Map; admin?: boolean }[] = [
  { href: '/map', label: 'Mapa', icon: Map },
  { href: '/search', label: 'Paraderos', icon: Search },
  { href: '/destinations', label: 'Destinos', icon: Navigation },
  { href: '/simulacion', label: 'Simulación', icon: ChartColumn },
  { href: '/dashboard', label: 'Panel', icon: LayoutDashboard, admin: true },
  { href: '/account', label: 'Cuenta', icon: User },
];

const iniciales = (name?: string) =>
  (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join('');

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, connectionError, retry, isAdmin } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user && !connectionError) {
      router.replace(isAdminRoute(pathname) ? `/login?continuar=${pathname.split('/')[1]}` : '/login');
    }
  }, [loading, user, connectionError, pathname, router]);

  if (connectionError) {
    return (
      <div className="flex h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-base font-semibold text-fg">No pudimos conectar con el servidor</p>
        <p className="max-w-sm text-sm text-muted">Puede estar despertando o tu conexión falló. Tu sesión sigue guardada.</p>
        <button onClick={retry} className="btn btn-primary">Reintentar</button>
      </div>
    );
  }

  if (loading || !user) {
    return <div className="flex h-dvh items-center justify-center"><Spinner size={28} /></div>;
  }

  const items = NAV.filter((item) => !item.admin || isAdmin);
  const restringida = isAdminRoute(pathname) && !isAdmin;
  const isActive = (href: string) => pathname === href || (href === '/search' && pathname.startsWith('/station'));

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      {/* Barra lateral: tablet y escritorio */}
      <aside className="mobility-nav hidden w-[4.5rem] shrink-0 flex-col border-r border-line md:flex lg:w-60">
        <Link href="/map" className="mobility-nav-brand flex h-20 items-center justify-center border-b px-5 lg:justify-start">
          <Logo size={30} showText={false} />
          <span className="ml-2.5 hidden text-lg font-bold tracking-tight lg:block">UrbanSafe</span>
        </Link>

        <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Principal">
          {items.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                title={label}
                aria-current={active ? 'page' : undefined}
                className="mobility-nav-link relative flex items-center justify-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors lg:justify-start"
              >
                <Icon size={19} strokeWidth={active ? 2.25 : 2} />
                <span className="hidden lg:block">{label}</span>
              </Link>
            );
          })}
        </nav>


        <div className="mobility-nav-user flex items-stretch border-t">
          <Link href="/account" aria-label={`Ir a mi cuenta: ${user.name}`} className="flex min-w-0 flex-1 items-center justify-center gap-2.5 p-3 hover:bg-surface-2 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand lg:justify-start" title="Ir a mi cuenta">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
              {iniciales(user.name)}
            </span>
            <span className="hidden min-w-0 lg:block">
              <span className="block truncate text-sm font-medium text-fg">{user.name}</span>
              <span className="block truncate text-xs text-muted">{user.email}</span>
            </span>
          </Link>
          <ThemeToggle className="mr-2 hidden self-center lg:inline-flex" />
        </div>
      </aside>

      <a href="#contenido" className="us-skip-link">Saltar al contenido</a>
      <main id="contenido" tabIndex={-1} className="min-h-0 min-w-0 flex-1 overflow-y-auto">
        <div key={pathname} className="page-in h-full">{restringida ? <AccesoRestringido /> : children}</div>
      </main>

      {/* Barra inferior: móvil */}
      <div className="us-mobile-nav md:hidden">
        <BottomNavigation component="nav" aria-label="Principal" showLabels value={items.find((item) => isActive(item.href))?.href ?? false}
          sx={{ background: 'var(--surface)', height: 68, '& .MuiBottomNavigationAction-root': { minWidth: 0, padding: '6px 2px', color: 'var(--muted)' },
            '& .Mui-selected': { color: 'var(--brand)' }, '& .MuiBottomNavigationAction-label': { fontSize: '0.65rem', marginTop: '4px', '&.Mui-selected': { fontSize: '0.65rem', fontWeight: 700 } } }}>
          {items.map(({ href, label, icon: Icon }) => <BottomNavigationAction component={Link} key={href} href={href}
            value={href} label={label} icon={<Icon size={20} />} aria-current={isActive(href) ? 'page' : undefined} />)}
        </BottomNavigation>
      </div>
    </div>
  );
}

function AccesoRestringido() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-2 text-muted"><ShieldAlert size={22} aria-hidden /></span>
      <h1 className="text-lg font-bold text-fg">Acceso restringido</h1>
      <p className="max-w-sm text-sm text-muted">Esta sección es solo para la cuenta de administración. Tu cuenta puede usar el mapa, los paraderos, los destinos y la simulación.</p>
      <Link href="/map" className="btn btn-primary mt-2">Volver al mapa</Link>
    </div>
  );
}
