'use client';

import { useId, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface Props {
  header: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

// Hoja inferior estilo Uber: se pliega para ver el mapa sin cerrar la búsqueda (toca o arrastra el asa; con teclado,
// Enter/Espacio). Plegada deja visible el encabezado (destino y botón de cerrar). En escritorio es una tarjeta flotante.
export default function BottomSheet({ header, children, className = '' }: Props) {
  const [open, setOpen] = useState(true);
  const startY = useRef<number | null>(null);
  const contentId = useId();

  const onPointerDown = (e: React.PointerEvent) => {
    startY.current = e.clientY;
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerUp = (e: React.PointerEvent) => {
    if (startY.current === null) return;
    const dy = e.clientY - startY.current;
    startY.current = null;
    if (dy > 30) setOpen(false);
    else if (dy < -30) setOpen(true);
    else setOpen((v) => !v);
  };

  return (
    <div className={`float-panel animate-sheet-in overflow-hidden ${className}`}>
      <button
        type="button"
        aria-label={open ? 'Plegar panel' : 'Desplegar panel'}
        aria-expanded={open}
        aria-controls={contentId}
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen((v) => !v); } }}
        className="group flex w-full cursor-grab touch-none justify-center pb-0.5 pt-2 outline-none active:cursor-grabbing"
      >
        <span className="flex h-7 w-16 items-center justify-center rounded-full bg-surface-2 text-muted outline-2 outline-offset-0 outline-transparent transition-colors group-hover:text-fg group-focus-visible:outline-brand">
          <ChevronDown size={18} className={`transition-transform duration-300 ${open ? '' : 'rotate-180'}`} />
        </span>
      </button>
      {header}
      <div className={`grid transition-[grid-template-rows] duration-300 ease-out ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
        <div id={contentId} inert={!open} className="scroll-thin min-h-0 max-h-[52dvh] overflow-y-auto md:max-h-[calc(100dvh-17rem)]">{children}</div>
      </div>
    </div>
  );
}
