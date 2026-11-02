import { CheckCircle2, Info, TriangleAlert, OctagonAlert } from 'lucide-react';

type Tono = 'info' | 'ok' | 'warn' | 'danger';

const ESTILO: Record<Tono, { clase: string; Icono: React.ComponentType<{ size?: number; className?: string }> }> = {
  info: { clase: 'bg-surface-2 text-fg', Icono: Info },
  ok: { clase: 'bg-ok/12 text-ok', Icono: CheckCircle2 },
  warn: { clase: 'bg-warn/12 text-warn', Icono: TriangleAlert },
  danger: { clase: 'bg-danger/12 text-danger', Icono: OctagonAlert },
};

// Aviso en línea con ícono y texto (el color nunca es la única señal)
export default function Alert({ tono = 'info', children, className = '' }: { tono?: Tono; children: React.ReactNode; className?: string }) {
  const { clase, Icono } = ESTILO[tono];
  return (
    <div role={tono === 'danger' ? 'alert' : 'status'} className={`flex gap-2.5 rounded-xl px-3.5 py-3 text-sm ${clase} ${className}`}>
      <Icono size={16} className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
