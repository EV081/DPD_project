'use client';

import { useCallback, useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';
import Alert from './Alert';
import { Skeleton } from './Spinner';
import { errorMessage } from '@/lib/client';
import { getMisReportes, ReporteMio, retirarReporte, TIPOS_REPORTE } from '@/lib/eje2';

const fecha = (iso: string) =>
  new Date(iso).toLocaleString('es-PE', { timeZone: 'America/Lima', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });

// Solo los reportes del propio usuario; retirarlos los saca del cálculo de riesgo
export default function MisReportes() {
  const [items, setItems] = useState<ReporteMio[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retirando, setRetirando] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try { setItems(await getMisReportes()); }
    catch (e) { setError(errorMessage(e, 'No se pudieron cargar tus reportes.')); setItems([]); }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const retirar = async (id: string) => {
    setRetirando(id);
    try { await retirarReporte(id); await cargar(); }
    catch (e) { setError(errorMessage(e, 'No se pudo retirar el reporte.')); }
    finally { setRetirando(null); }
  };

  if (items === null) return <Skeleton className="h-16 w-full" />;

  return (
    <div>
      {error && <Alert tono="danger" className="m-4">{error}</Alert>}
      {items.length === 0 && !error ? (
        <p className="px-5 py-4 text-sm text-muted">Aún no has reportado incidentes. Puedes hacerlo desde el mapa.</p>
      ) : (
        <ul className="divide-y divide-line">
          {items.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
              <div className="min-w-0">
                <p className="text-sm font-medium text-fg">{TIPOS_REPORTE.find((t) => t.id === r.tipo)?.label ?? r.tipo}
                  {r.estado === 'retirado' && <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-muted">Retirado</span>}
                </p>
                <p className="text-xs text-muted">{fecha(r.ocurrido_en || r.creado_en)} · {r.franja === 'noche' ? 'noche' : 'día'}</p>
              </div>
              {r.estado === 'activo' && (
                <button onClick={() => retirar(r.id)} disabled={retirando === r.id} aria-label={`Retirar reporte de ${r.tipo}`} className="btn btn-ghost !p-2">
                  <Trash2 size={16} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
