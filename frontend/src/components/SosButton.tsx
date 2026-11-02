'use client';

import { useState } from 'react';
import { Phone, ShieldAlert } from 'lucide-react';
import Modal from './Modal';
import Alert from './Alert';
import { NUMERO_EMERGENCIA } from '@/lib/eje2';

// Botón de alerta: ofrece llamar al 105 (Policía Nacional) y recuerda qué hacer
export default function SosButton({ className = '', onReport }: { className?: string; onReport?: () => void }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} aria-label="Emergencia: llamar al 105" className={`btn btn-sos !rounded-2xl !px-3.5 shadow-[var(--shadow-float)] ${className}`}>
        <ShieldAlert size={18} /> <span className="hidden sm:inline">SOS</span>
      </button>
      {open && (
        <Modal title="¿Necesitas ayuda?" onClose={() => setOpen(false)}>
          <p className="mb-4 text-sm text-muted">
            Si estás en peligro, llama a la Policía Nacional. UrbanSafe no avisa a nadie por ti.
          </p>
          <a href={`tel:${NUMERO_EMERGENCIA}`} className="btn btn-sos w-full !py-4 !text-lg">
            <Phone size={20} /> Llamar al {NUMERO_EMERGENCIA}
          </a>
          <ul className="mt-4 space-y-1.5 text-sm text-fg">
            <li>• Ve a un lugar iluminado y con gente (tienda, paradero concurrido).</li>
            <li>• Si te siguen, entra a un local y pide ayuda.</li>
            <li>• Comparte tu ubicación con alguien de confianza.</li>
          </ul>
          {onReport && (
            <button type="button" className="btn btn-secondary mt-4 w-full" onClick={() => { setOpen(false); onReport(); }}>
              Reportar lo que ocurrió
            </button>
          )}
          <Alert tono="info" className="mt-4">Un reporte en la app no sustituye una denuncia ni activa ayuda inmediata.</Alert>
        </Modal>
      )}
    </>
  );
}
