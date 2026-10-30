import { forwardRef } from 'react';

interface Props extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  hint?: string;
}

// Campo de formulario con etiqueta asociada, icono opcional y ayuda
export const Field = forwardRef<HTMLInputElement, Props>(function Field({ label, icon: Icon, hint, id, className = '', ...rest }, ref) {
  const fid = id || `f-${label.toLowerCase().replace(/\W+/g, '-')}`;
  return (
    <div className={className}>
      <label htmlFor={fid} className="mb-1.5 block text-sm font-medium text-fg">{label}</label>
      <div className="relative">
        {Icon && <Icon size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />}
        <input ref={ref} id={fid} className={`input ${Icon ? '!pl-10' : ''}`} {...rest} />
      </div>
      {hint && <p className="mt-1.5 text-xs text-muted">{hint}</p>}
    </div>
  );
});

export function ErrorNote({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2.5 text-sm text-rose-700 dark:text-rose-300">
      {children}
    </p>
  );
}
