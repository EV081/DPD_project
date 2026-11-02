'use client';

import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

interface Props {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  /** Se pasa al contenedor: p. ej. z-index mayor que el del mapa. */
  className?: string;
}

// Diálogo accesible: foco al abrir, Escape y clic fuera cierran, el foco vuelve al botón que lo abrió
export default function Modal({ title, onClose, children, className = '' }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useEffect(() => {
    const previo = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab' && ref.current) {   // el foco no sale del diálogo
        const f = ref.current.querySelectorAll<HTMLElement>('a[href],button:not(:disabled),input,select,textarea,[tabindex]:not([tabindex="-1"])');
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); previo?.focus?.(); };
  }, [onClose]);

  return (
    <div className={`fixed inset-0 z-[2000] flex items-end justify-center bg-black/50 p-3 sm:items-center ${className}`} onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}
        className="float-panel animate-sheet-in max-h-[90dvh] w-full max-w-md overflow-y-auto outline-none">
        <div className="flex items-start justify-between gap-3 px-5 pb-2 pt-5">
          <h2 id={titleId} className="text-lg font-bold text-fg">{title}</h2>
          <button onClick={onClose} aria-label="Cerrar" className="btn btn-ghost !rounded-full !bg-surface-2 !p-2"><X size={18} /></button>
        </div>
        <div className="px-5 pb-5">{children}</div>
      </div>
    </div>
  );
}
