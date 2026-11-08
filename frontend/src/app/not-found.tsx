'use client';

import Link from 'next/link';
import { Compass, Home, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-4 py-12 text-center bg-surface">
      <div className="card rise max-w-md w-full p-8 border border-line shadow-lg">
        {/* Icono decorativo representativo */}
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-soft text-brand mb-6">
          <Compass size={32} className="animate-pulse" />
        </div>

        <span className="font-mono text-xs font-semibold text-brand tracking-widest uppercase">
          Error 404
        </span>
        
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-fg">
          Página no encontrada
        </h1>
        
        <p className="mt-2 text-sm text-muted leading-relaxed">
          Lo sentimos, la ruta o estación que buscas no existe, fue movida o el enlace es incorrecto.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link href="/map" className="btn btn-primary w-full sm:w-auto flex items-center justify-center gap-2">
            <Home size={16} />
            Ir al Mapa
          </Link>
          
          <button 
            onClick={() => window.history.back()} 
            className="btn btn-secondary w-full sm:w-auto flex items-center justify-center gap-2"
          >
            <ArrowLeft size={16} />
            Volver atrás
          </button>
        </div>
      </div>
    </div>
  );
}