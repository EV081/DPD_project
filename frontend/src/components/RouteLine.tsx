// Motivo de marca: una línea de transporte cuyos tramos muestran el aforo previsto.
// El color nunca es la única señal: cada paradero lleva su etiqueta de texto.
const PARADAS = [
  { nombre: 'Naranjal', aforo: 'Asientos', color: '#4ade80' },
  { nombre: 'UNI', aforo: 'De pie', color: '#fbbf24' },
  { nombre: 'Central', aforo: 'Saturado', color: '#f87171' },
  { nombre: 'Angamos', aforo: 'De pie', color: '#fbbf24' },
  { nombre: 'Matellini', aforo: 'Asientos', color: '#4ade80' },
];

/** Vertical (panel de escritorio) */
export function RouteLine({ className = '' }: { className?: string }) {
  return (
    <ol className={`relative ${className}`} aria-label="Ejemplo de aforo previsto en el Metropolitano">
      <span aria-hidden className="line-v absolute bottom-3 left-[0.6875rem] top-3 w-[3px] rounded-full bg-gradient-to-b from-green-400 via-amber-300 via-50% to-green-400 opacity-70" />
      {PARADAS.map((p, i) => (
        <li key={p.nombre} className="relative flex items-center gap-4 py-2.5">
          <span aria-hidden className="stop-pop relative z-10 h-6 w-6 shrink-0 rounded-full border-[5px] border-[#0d2a63] ring-2" style={{ '--i': i, backgroundColor: p.color, boxShadow: `0 0 0 2px ${p.color}` } as React.CSSProperties} />
          <span className="rise flex flex-1 items-baseline justify-between gap-3 text-sm" style={{ '--i': i + 2 } as React.CSSProperties}>
            <span className="font-semibold">{p.nombre}</span>
            <span className="text-blue-100/75">{p.aforo}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

/** Horizontal compacta (hero móvil) */
export function RouteLineMini({ className = '' }: { className?: string }) {
  return (
    <div className={`relative ${className}`} role="img" aria-label="Línea de transporte con aforo previsto: asientos, de pie, saturado, de pie, asientos">
      <span aria-hidden className="line-h absolute left-2 right-2 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-gradient-to-r from-green-400 via-amber-300 to-green-400 opacity-70" />
      <div className="relative flex justify-between" aria-hidden>
        {PARADAS.map((p, i) => (
          <span key={p.nombre} className="stop-pop h-4 w-4 rounded-full border-[3px] border-[#123a86]" style={{ '--i': i, backgroundColor: p.color, boxShadow: `0 0 0 2px ${p.color}` } as React.CSSProperties} />
        ))}
      </div>
    </div>
  );
}
