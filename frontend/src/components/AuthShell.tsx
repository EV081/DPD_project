import Image from 'next/image';
import { ShieldCheck, Gauge, Route } from 'lucide-react';
import { Logo } from './Logo';
import { ThemeToggle } from './ThemeToggle';

const PUNTOS = [
  { icon: Gauge, titulo: 'Aforo pronosticado', texto: 'Sabe si el bus llega con asientos, de pie o saturado antes de salir.' },
  { icon: Route, titulo: 'Rutas directas', texto: 'Te sugerimos dónde subir según caminata, espera y ocupación.' },
  { icon: ShieldCheck, titulo: 'Datos oficiales ATU', texto: 'Modelos entrenados con las validaciones de 2025 del sistema integrado.' },
];

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
          <h1 className="text-4xl font-bold leading-tight tracking-tight">
            Viaja por Lima sabiendo cómo viene el bus.
          </h1>
          <p className="mt-4 text-lg text-blue-100/80">
            Predicción de aforo y tiempos de espera para el Metropolitano, corredores, alimentadores y la Línea 1.
          </p>
          <ul className="mt-10 space-y-6">
            {PUNTOS.map(({ icon: Icon, titulo, texto }) => (
              <li key={titulo} className="flex gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                  <Icon size={20} />
                </span>
                <span>
                  <span className="block font-semibold">{titulo}</span>
                  <span className="block text-sm text-blue-100/75">{texto}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative flex items-center gap-4 text-sm text-blue-100/70">
          <Image src="/img/utec_completo.png" alt="UTEC" width={96} height={72} className="h-14 w-auto opacity-90" />
          <span>Proyecto de Desarrollo de Producto de Datos · UTEC</span>
        </div>
      </aside>

      <main className="relative flex flex-col justify-center px-5 py-10 sm:px-10">
        <div className="absolute right-4 top-4"><ThemeToggle /></div>
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-8 lg:hidden"><Logo size={34} /></div>
          {children}
        </div>
      </main>
    </div>
  );
}
