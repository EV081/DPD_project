'use client';

import DataTable from '@/components/DataTable';
import { SegmentedControl } from '@mantine/core';
import { useEffect, useId, useState, type ReactNode } from 'react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { CheckCircle2, Minus, Table2, TriangleAlert, XCircle, BarChart3 } from 'lucide-react';

/* Piezas del panel: tarjeta de gráfico con vista de tabla, gráficos con la paleta validada y estados con ícono + texto. */

export const ENTERO = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 });
export const DECIMAL = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 });

export const SISTEMAS_MODELO: Record<string, { label: string; token: string }> = {
  metro_l1: { label: 'Metro L1', token: 'var(--viz-metro_l1)' },
  troncal: { label: 'Metropolitano', token: 'var(--viz-troncal)' },
  corredor: { label: 'Corredores', token: 'var(--viz-corredor)' },
  alimentador: { label: 'Alimentadores', token: 'var(--viz-alimentador)' },
};
/** El backend usa nombres de modelo (troncal, corredor…) y de catálogo (metropolitano, corredores…): se unifican. */
const ALIAS: Record<string, string> = { metropolitano: 'troncal', corredores: 'corredor', alimentadores: 'alimentador' };
export const claveSistema = (s: string) => ALIAS[s] ?? s;
export const infoSistema = (s: string) => SISTEMAS_MODELO[claveSistema(s)] ?? { label: s, token: 'var(--viz-1)' };

export const fechaCorta = (iso: string) => {
  const [, m, d] = iso.slice(0, 10).split('-');
  return `${d}/${m}`;
};

function useReducedMotion() {
  const [reducido, setReducido] = useState(false);
  useEffect(() => {
    const q = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducido(q.matches);
    const f = () => setReducido(q.matches);
    q.addEventListener('change', f);
    return () => q.removeEventListener('change', f);
  }, []);
  return reducido;
}

/* ---------- Tarjeta con vista de gráfico / tabla ---------- */
export interface Tabla { cabeceras: string[]; filas: (string | number)[][] }

export function ChartCard({ titulo, descripcion, tabla, vacio, children, className = '' }: {
  titulo: string; descripcion?: string; tabla: Tabla; vacio?: string; children: ReactNode; className?: string;
}) {
  const [verTabla, setVerTabla] = useState(false);
  return (
    <section className={`card flex min-w-0 flex-col p-4 sm:p-5 ${className}`} aria-label={titulo}>
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-fg">{titulo}</h3>
          {descripcion && <p className="mt-0.5 text-xs text-muted">{descripcion}</p>}
        </div>
        <SegmentedControl size="xs" value={verTabla ? 'tabla' : 'grafico'} onChange={(v) => setVerTabla(v === 'tabla')}
          aria-label={`Vista de ${titulo}`} data={[
            { value: 'grafico', label: <span className="flex items-center gap-1"><BarChart3 size={14} /> Gráfico</span> },
            { value: 'tabla', label: <span className="flex items-center gap-1"><Table2 size={14} /> Tabla</span> },
          ]} />
      </header>
      <div className="mt-3 min-h-0 flex-1">
        {vacio ? <p className="flex h-40 items-center justify-center rounded-xl bg-surface-2 px-4 text-center text-sm text-muted">{vacio}</p>
          : verTabla ? <TablaDatos tabla={tabla} titulo={titulo} /> : children}
      </div>
    </section>
  );
}

export function TablaDatos({ tabla, titulo }: { tabla: Tabla; titulo: string }) {
  const columns = tabla.cabeceras.map((label, i) => ({ id: String(i), label, value: (row: (string | number)[]) => row[i] }));
  return <DataTable rows={tabla.filas} columns={columns} title={titulo} />;
}

/* ---------- Tooltip: valor primero, nombre después, clave con trazo corto ---------- */
interface PuntoTip { dataKey?: string | number; name?: string; value?: number | string; color?: string; stroke?: string; fill?: string; payload?: Record<string, unknown> }

function Tip({ active, payload, label, formato, titulo }: {
  active?: boolean; payload?: readonly PuntoTip[]; label?: string | number; formato: (v: number) => string; titulo?: (l: string | number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-[var(--shadow-float)]">
      <p className="mb-1 text-muted">{titulo && label !== undefined ? titulo(label) : String(label ?? '')}</p>
      {payload.map((p, i) => {
        const v = typeof p.value === 'number' ? p.value : Number(p.value);
        return (
          <p key={`${p.dataKey}-${i}`} className="flex items-center gap-2 leading-5">
            <span aria-hidden className="h-0.5 w-3 shrink-0 rounded" style={{ background: p.stroke ?? p.fill ?? p.color }} />
            <strong className="tabular-nums text-fg">{Number.isFinite(v) ? formato(v) : 'sin dato'}</strong>
            <span className="text-muted">{p.name}</span>
          </p>
        );
      })}
    </div>
  );
}

const EJES = { stroke: 'var(--viz-grid)', tickLine: false } as const;

/* ---------- Columnas (una serie, color de magnitud) ---------- */
export function Columnas({ datos, x, y = 'n', nombre, formatoX, formatoTip, altura = 200 }: {
  datos: Record<string, unknown>[]; x: string; y?: string; nombre: string; formatoX?: (v: string | number) => string;
  formatoTip?: (l: string | number) => string; altura?: number;
}) {
  const reducido = useReducedMotion();
  return (
    <div style={{ height: altura }} role="img" aria-label={`Gráfico de columnas: ${nombre}. Use la vista de tabla para leer los valores.`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos} margin={{ top: 8, right: 4, bottom: 0, left: -12 }} accessibilityLayer>
          <CartesianGrid vertical={false} stroke="var(--viz-grid)" strokeWidth={1} />
          <XAxis dataKey={x} {...EJES} tickFormatter={formatoX} interval="preserveStartEnd" minTickGap={14} />
          <YAxis {...EJES} axisLine={false} allowDecimals={false} width={44} />
          <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={<Tip formato={(v) => ENTERO.format(v)} titulo={formatoTip} />} />
          <Bar dataKey={y} name={nombre} fill="var(--viz-1)" radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={!reducido} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ---------- Barras horizontales (categorías con nombre en el eje; color por sistema opcional) ---------- */
export function BarrasH({ datos, nombre, altura }: {
  datos: { etiqueta: string; n: number; color?: string }[]; nombre: string; altura?: number;
}) {
  const reducido = useReducedMotion();
  const h = altura ?? Math.max(120, datos.length * 44 + 24);
  return (
    <div style={{ height: h }} role="img" aria-label={`Gráfico de barras: ${nombre}. Use la vista de tabla para leer los valores.`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos} layout="vertical" margin={{ top: 0, right: 40, bottom: 0, left: 0 }} accessibilityLayer>
          <CartesianGrid horizontal={false} stroke="var(--viz-grid)" strokeWidth={1} />
          <XAxis type="number" {...EJES} axisLine={false} allowDecimals={false} />
          <YAxis type="category" dataKey="etiqueta" {...EJES} width={108} />
          <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={<Tip formato={(v) => ENTERO.format(v)} />} />
          <Bar dataKey="n" name={nombre} radius={[0, 4, 4, 0]} maxBarSize={24} isAnimationActive={!reducido}
            label={{ position: 'right', fill: 'var(--fg)', fontSize: 11, formatter: (v: unknown) => ENTERO.format(Number(v)) }}
            shape={(p: { x?: number; y?: number; width?: number; height?: number; payload?: { color?: string } }) => {
              const { x = 0, y = 0, width = 0, height = 0, payload } = p;
              const w = Math.max(width, 0), r = Math.min(4, w, height / 2);      // extremo de datos redondeado (4 px), base recta
              return <path d={`M${x},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + height - r} Q${x + w},${y + height} ${x + w - r},${y + height} H${x} Z`} fill={payload?.color ?? 'var(--viz-1)'} />;
            }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ---------- Líneas por sistema (leyenda siempre visible: identidad nunca solo por color) ---------- */
export function LineasSistemas({ datos, series, formato, formatoTip, dominio, altura = 220 }: {
  datos: Record<string, unknown>[]; series: string[]; formato: (v: number) => string; formatoTip?: (l: string | number) => string;
  dominio?: [number | 'auto', number | 'auto']; altura?: number;
}) {
  const reducido = useReducedMotion();
  return (
    <div>
      <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1" aria-label="Leyenda">
        {series.map((s) => (
          <li key={s} className="flex items-center gap-1.5 text-xs text-muted">
            <span aria-hidden className="h-0.5 w-4 rounded" style={{ background: infoSistema(s).token }} />{infoSistema(s).label}
          </li>
        ))}
      </ul>
      <div style={{ height: altura }} role="img" aria-label="Gráfico de líneas por sistema. Use la vista de tabla para leer los valores.">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: -8 }} accessibilityLayer>
            <CartesianGrid vertical={false} stroke="var(--viz-grid)" strokeWidth={1} />
            <XAxis dataKey="semana" {...EJES} tickFormatter={(v) => fechaCorta(String(v))} />
            <YAxis {...EJES} axisLine={false} width={48} tickFormatter={formato} domain={dominio ?? [0, 'auto']} />
            <Tooltip cursor={{ stroke: 'var(--viz-grid)' }} content={<Tip formato={formato} titulo={formatoTip} />} />
            {series.map((s) => (
              <Line key={s} type="monotone" dataKey={s} name={infoSistema(s).label} stroke={infoSistema(s).token} strokeWidth={2}
                strokeLinecap="round" strokeLinejoin="round" connectNulls isAnimationActive={!reducido}
                dot={{ r: 4, fill: infoSistema(s).token, stroke: 'var(--surface)', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: infoSistema(s).token, stroke: 'var(--surface)', strokeWidth: 2 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ---------- Estado con ícono + texto (el color nunca es la única señal) ---------- */
export type Nivel = 'ok' | 'warn' | 'error' | 'muted';
const NIVELES: Record<Nivel, { Icono: typeof CheckCircle2; clase: string }> = {
  ok: { Icono: CheckCircle2, clase: 'text-ok' },
  warn: { Icono: TriangleAlert, clase: 'text-warn' },
  error: { Icono: XCircle, clase: 'text-danger' },
  muted: { Icono: Minus, clase: 'text-muted' },
};

export function Estado({ nivel, children }: { nivel: Nivel; children: ReactNode }) {
  const { Icono, clase } = NIVELES[nivel];
  return <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${clase}`}><Icono size={14} aria-hidden />{children}</span>;
}

/* ---------- Tile de cifra ---------- */
export function Cifra({ etiqueta, valor, detalle, nivel }: { etiqueta: string; valor: string; detalle?: string; nivel?: Nivel }) {
  return (
    <div className="card p-4">
      <p className="text-xs font-medium text-muted">{etiqueta}</p>
      <p className="mt-1 text-3xl font-bold tracking-tight text-fg">{valor}</p>
      {detalle && <p className="mt-1 text-xs text-muted">{nivel ? <Estado nivel={nivel}>{detalle}</Estado> : detalle}</p>}
    </div>
  );
}

/** Tendencia temporal con relleno ligero, datos reales y tabla alternativa. */
export function Tendencia({ datos, x, nombre, formatoX, formatoTip }: {
  datos: Record<string, unknown>[]; x: string; nombre: string;
  formatoX?: (value: string | number) => string; formatoTip?: (value: string | number) => string;
}) {
  const reducido = useReducedMotion();
  const gradient = useId().replace(/:/g, '');
  return <div style={{ height: 220 }} role="img" aria-label={`Tendencia de ${nombre}. Valores disponibles en la vista de tabla.`}>
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={datos} margin={{ top: 12, right: 12, bottom: 0, left: -12 }} accessibilityLayer>
        <defs><linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--viz-1)" stopOpacity={0.25} /><stop offset="100%" stopColor="var(--viz-1)" stopOpacity={0.02} /></linearGradient></defs>
        <CartesianGrid vertical={false} stroke="var(--viz-grid)" strokeDasharray="3 3" />
        <XAxis dataKey={x} {...EJES} tickFormatter={formatoX} minTickGap={24} />
        <YAxis {...EJES} axisLine={false} allowDecimals={false} width={44} />
        <Tooltip content={<Tip formato={(v) => ENTERO.format(v)} titulo={formatoTip} />} />
        <Area type="monotone" dataKey="n" name={nombre} stroke="var(--viz-1)" strokeWidth={2.5} fill={`url(#${gradient})`} isAnimationActive={!reducido} />
      </AreaChart>
    </ResponsiveContainer>
  </div>;
}
