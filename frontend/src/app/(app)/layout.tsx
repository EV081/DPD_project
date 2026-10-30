'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Map, Search, Navigation, User } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Logo } from '@/components/Logo';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Spinner } from '@/components/Spinner';

const NAV = [
  { href: '/map', label: 'Mapa', icon: Map },
  { href: '/search', label: 'Paraderos', icon: Search },
  { href: '/destinations', label: 'Destinos', icon: Navigation },
  { href: '/account', label: 'Cuenta', icon: User },
];

const iniciales = (name?: string) =>
  (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join('');

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace('/login');
  }, [loading, user, router]);

  if (loading || !user) {
    return <div className="flex h-dvh items-center justify-center"><Spinner size={28} /></div>;
  }

  const isActive = (href: string) => pathname === href || (href === '/search' && pathname.startsWith('/station'));

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      {/* Barra lateral: tablet y escritorio */}
      <aside className="hidden w-[4.5rem] shrink-0 flex-col border-r border-line bg-surface md:flex lg:w-64">
        <Link href="/map" className="flex h-16 items-center justify-center border-b border-line px-5 lg:justify-start">
          <Logo size={30} showText={false} />
          <span className="ml-2.5 hidden text-lg font-bold tracking-tight text-fg lg:block">UrbanSafe</span>
        </Link>

        <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Principal">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                title={label}
                aria-current={active ? 'page' : undefined}
                className={`flex items-center justify-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors lg:justify-start ${
                  active ? 'bg-brand-soft text-brand' : 'text-muted hover:bg-surface-2 hover:text-fg'
                }`}
              >
                <Icon size={19} strokeWidth={active ? 2.25 : 2} />
                <span className="hidden lg:block">{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center justify-center gap-2 border-t border-line p-3 lg:justify-between">
          <Link href="/account" className="flex min-w-0 items-center gap-2.5 rounded-lg p-1 hover:bg-surface-2" title={user.name}>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
              {iniciales(user.name)}
            </span>
            <span className="hidden min-w-0 lg:block">
              <span className="block truncate text-sm font-medium text-fg">{user.name}</span>
              <span className="block truncate text-xs text-muted">{user.email}</span>
            </span>
          </Link>
          <ThemeToggle className="hidden lg:inline-flex" />
        </div>
      </aside>

      <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">{children}</main>

      {/* Barra inferior: móvil */}
      <nav
        aria-label="Principal"
        className="grid shrink-0 grid-cols-4 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? 'page' : undefined}
              className={`flex flex-col items-center gap-1 py-2.5 text-xs font-medium ${active ? 'text-brand' : 'text-muted'}`}
            >
              <Icon size={20} strokeWidth={active ? 2.25 : 2} />
              {label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
