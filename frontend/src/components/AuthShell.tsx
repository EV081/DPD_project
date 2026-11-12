import { ChartNoAxesCombined, Navigation, Clock3 } from 'lucide-react';
import Link from 'next/link';
import { Logo } from './Logo';
import { ThemeToggle } from './ThemeToggle';
import RutaAnimada from './RutaAnimada';

const PASOS = [
  { icon: Navigation, titulo: 'Elige tu destino', texto: 'Encuentra opciones de transporte.' },
  { icon: Clock3, titulo: 'Compara tu viaje', texto: 'Revisa espera, caminata y aforo.' },
  { icon: ChartNoAxesCombined, titulo: 'Explora por hora', texto: 'Prueba un escenario histórico.' },
];

// El acceso conserva el mismo formulario y la misma autenticación.
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mobility-entry">
      <aside className="mobility-story">
        <header className="mobility-story-top">
          <div className="flex items-center gap-2.5"><Logo size={32} showText={false} /><span className="text-xl font-bold tracking-tight">UrbanSafe</span></div>
          <span className="mobility-tag">Movilidad · Lima</span>
        </header>

        <div className="mobility-story-copy">
          <p className="mobility-kicker"><span /> Antes de salir</p>
          <h1>El viaje empieza<br />antes de subir.</h1>
          <p>Conoce tus opciones, compara horarios y mira el transporte de Lima desde los datos.</p>
        </div>

        <RutaAnimada className="mobility-story-image" />

        <div className="mobility-steps">
          {PASOS.map(({ icon: Icon, titulo, texto }, indice) => (
            <div key={titulo}>
              <span className="mobility-step-number">0{indice + 1}<Icon size={17} /></span>
              <h2>{titulo}</h2>
              <p>{texto}</p>
            </div>
          ))}
        </div>
        <p className="mobility-source">Aforo estimado con datos ATU. No es un conteo en vivo.</p>
      </aside>

      <main id="acceso" className="mobility-access">
        <div className="mobility-access-top"><Link href="/" className="hover:underline">← Volver al inicio</Link><ThemeToggle /></div>
        <div className="mobility-access-form">
          <div className="stagger">{children}</div>
          <div className="mobility-access-note"><span className="mobility-mini-dot" /><p>Explora el mapa, compara rutas y ensaya escenarios en la misma cuenta.</p></div>
        </div>
        <footer className="mobility-access-footer"><span>UrbanSafe</span><span>Un proyecto de estudiantes · UTEC</span></footer>
      </main>
    </div>
  );
}
