import Image from 'next/image';
import { Logo } from './Logo';
import { RouteLine, RouteLineMini } from './RouteLine';
import { ThemeToggle } from './ThemeToggle';

// Estructura de login y registro: panel de marca a la izquierda (solo escritorio) y formulario a la derecha
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,34rem)]">
      <aside className="relative hidden overflow-hidden bg-[#0d2a63] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-blue-500/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-sky-400/20 blur-3xl" />

        <div className="relative flex items-center gap-2.5">
          <Logo size={34} showText={false} />
          <span className="text-xl font-bold tracking-tight">UrbanSafe</span>
        </div>

        <div className="relative max-w-lg">
          <h1 className="rise text-4xl font-bold leading-tight tracking-tight">
            Viaja por Lima sabiendo cómo viene el bus.
          </h1>
          <p className="mt-4 text-lg text-blue-100/80">
            Predicción de aforo y tiempos de espera para el Metropolitano, corredores, alimentadores y la Línea 1.
          </p>
          <RouteLine className="mt-10 max-w-xs" />
          <p className="mt-4 text-sm text-blue-100/70">Así vemos cada tramo: asientos, de pie o saturado, hora a hora.</p>
        </div>

        <div className="relative flex items-center gap-4 text-sm text-blue-100/70">
          <Image src="/img/utec_completo.png" alt="UTEC" width={96} height={72} className="h-14 w-auto opacity-90" />
          <span>Proyecto de Desarrollo de Producto de Datos · UTEC</span>
        </div>
      </aside>

      <main className="relative flex flex-col justify-center px-5 py-10 sm:px-10">
        <div className="absolute right-4 top-4"><ThemeToggle /></div>
        <div className="mx-auto w-full max-w-sm">
          <div className="hero mb-8 p-6 lg:hidden">
            <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-sky-400/30 blur-2xl" />
            <div className="relative flex items-center gap-2.5"><Logo size={34} showText={false} /><span className="text-xl font-bold tracking-tight">UrbanSafe</span></div>
            <p className="relative mt-4 text-lg font-semibold leading-snug">Viaja por Lima sabiendo cómo viene el bus.</p>
            <RouteLineMini className="relative mt-5" />
          </div>
          <div className="stagger">{children}</div>
        </div>
      </main>
    </div>
  );
}
