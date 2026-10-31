'use client';

import { useRef, useState } from 'react';

interface Props {
  header: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

// Hoja inferior estilo Uber: en móvil se arrastra (o se toca el asa) para plegar el contenido;
// en pantallas grandes es una tarjeta flotante siempre desplegada.
export default function BottomSheet({ header, children, className = '' }: Props) {
  const [open, setOpen] = useState(true);
  const startY = useRef<number | null>(null);

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
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen((v) => !v); } }}
        className="flex w-full cursor-grab touch-none justify-center pb-1 pt-2.5 md:hidden"
      >
        <span className="h-1.5 w-10 rounded-full bg-line" />
      </button>
      {header}
      <div className={`grid transition-[grid-template-rows] duration-300 ease-out md:grid-rows-[1fr] ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
        <div className="scroll-thin min-h-0 max-h-[52dvh] overflow-y-auto md:max-h-[calc(100dvh-13rem)]">{children}</div>
      </div>
    </div>
  );
}
