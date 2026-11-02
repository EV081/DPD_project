'use client';

import { useState } from 'react';
import { Phone } from 'lucide-react';
import Modal from './Modal';
import Alert from './Alert';
import { Spinner } from './Spinner';
import { Coords } from '@/lib/geolocation';
import { errorMessage } from '@/lib/client';
import { crearReporte, NUMERO_EMERGENCIA, ReporteCreado, TIPOS_REPORTE, TipoReporte } from '@/lib/eje2';

const CUANDO = [
  { id: 'ahora', label: 'Ahora', horas: 0 },
  { id: '1h', label: 'Hace 1 h', horas: 1 },
  { id: '3h', label: 'Hace 3 h', horas: 3 },
  { id: '12h', label: 'Hace 12 h', horas: 12 },
];

// Reporte anónimo de un incidente en el punto donde estás (sin texto libre, sin datos de otras personas)
export default function ReportarModal({ ubicacion, ubicacionReal, onClose }: { ubicacion: Coords; ubicacionReal: boolean; onClose: () => void }) {
  const [tipo, setTipo] = useState<TipoReporte | null>(null);
  const [cuando, setCuando] = useState('ahora');
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hecho, setHecho] = useState<ReporteCreado | null>(null);

  const enviar = async () => {
    if (!tipo) return;
    setEnviando(true);
    setError(null);
    try {
      const horas = CUANDO.find((c) => c.id === cuando)?.horas ?? 0;
      const ocurrido = horas ? new Date(Date.now() - horas * 3600_000).toISOString() : undefined;
      setHecho(await crearReporte(tipo, ubicacion.lat, ubicacion.lon, ocurrido));
    } catch (e: any) {
      const s = e?.response?.status;
      setError(
        s === 422 ? 'Tu ubicación no está cerca de una calle con cobertura. Acércate a la calle donde ocurrió e inténtalo de nuevo.'
        : s === 429 ? errorMessage(e, 'Llegaste al límite de reportes. Inténtalo más tarde.')
        : s === 401 ? 'Tu sesión venció. Inicia sesión de nuevo.'
        : errorMessage(e, 'No se pudo enviar el reporte. Inténtalo de nuevo.'),
      );
    } finally {
      setEnviando(false);
    }
  };

  if (hecho) {
    return (
      <Modal title="Reporte enviado" onClose={onClose}>
        <Alert tono="ok">{hecho.mensaje}{hecho.calle ? ` (${hecho.calle})` : ''}</Alert>
        {hecho.llamar_105 && (
          <>
            <p className="mb-2 mt-4 text-sm text-fg">Si sigues en peligro, llama ahora:</p>
            <a href={`tel:${hecho.numero_emergencia || NUMERO_EMERGENCIA}`} className="btn btn-sos w-full"><Phone size={18} /> Llamar al {hecho.numero_emergencia || NUMERO_EMERGENCIA}</a>
          </>
        )}
        <p className="mt-4 text-xs text-muted">{hecho.aviso}</p>
        <button onClick={onClose} className="btn btn-secondary mt-4 w-full">Listo</button>
      </Modal>
    );
  }

  return (
    <Modal title="Reportar un incidente" onClose={onClose}>
      <p className="mb-4 text-sm text-muted">
        Se registra en la calle donde estás. Es anónimo para otras personas y ayuda a ajustar el riesgo de la zona cuando varias personas coinciden.
      </p>
      <fieldset>
        <legend className="eyebrow mb-2">¿Qué pasó?</legend>
        <div className="space-y-2">
          {TIPOS_REPORTE.map((t) => (
            <label key={t.id} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors ${tipo === t.id ? 'border-brand bg-brand-soft' : 'border-line hover:bg-surface-2'}`}>
              <input type="radio" name="tipo" className="mt-1 accent-[var(--brand)]" checked={tipo === t.id} onChange={() => setTipo(t.id)} />
              <span><span className="block text-sm font-semibold text-fg">{t.label}</span><span className="block text-xs text-muted">{t.hint}</span></span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="mt-4">
        <legend className="eyebrow mb-2">¿Cuándo?</legend>
        <div className="flex flex-wrap gap-2">
          {CUANDO.map((c) => (
            <button key={c.id} type="button" className="chip" data-active={cuando === c.id} aria-pressed={cuando === c.id} onClick={() => setCuando(c.id)}>{c.label}</button>
          ))}
        </div>
      </fieldset>

      {!ubicacionReal && <Alert tono="warn" className="mt-4">No tenemos tu ubicación: se usaría el centro de Lima. Activa el GPS para reportar.</Alert>}
      {error && <Alert tono="danger" className="mt-4">{error}</Alert>}

      <button onClick={enviar} disabled={!tipo || enviando || !ubicacionReal} className="btn btn-primary mt-5 w-full">
        {enviando ? <Spinner size={16} className="!text-white dark:!text-[#06101f]" /> : 'Enviar reporte'}
      </button>
      <p className="mt-3 text-xs text-muted">Los reportes son testimonios no verificados. Un reporte no reemplaza la denuncia ante la Policía.</p>
    </Modal>
  );
}
