'use client';

import { useMemo } from 'react';
import { useReducedMotion } from '@mantine/hooks';
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatoHora } from '@/lib/aforo';
import type { PredictionItem } from '@/lib/types';
import DataTable from './DataTable';

export default function OccupancyChart({ hours, first, second }: { hours: PredictionItem[]; first: string; second: string }) {
  const reduced = useReducedMotion();
  const data = useMemo(() => hours.map((item) => ({ hour: formatoHora(item.datetime),
    occupancy: item.class === 'Sin_servicio' || item.crowding == null ? null : Math.round(item.crowding * 100),
  })), [hours]);
  return <div className="mt-5">
    <div style={{ height: 240 }} role="img" aria-label="Ocupación por hora. Línea de referencia al cien por ciento. Valores disponibles en la tabla.">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 16, right: 12, bottom: 0, left: -16 }} accessibilityLayer>
          <CartesianGrid stroke="var(--line)" vertical={false} strokeDasharray="3 3" />
          <XAxis dataKey="hour" tick={{ fill: 'var(--muted)', fontSize: 11 }} minTickGap={24} tickLine={false} axisLine={false} />
          <YAxis domain={[0, (max: number) => Math.max(110, max)]} tickFormatter={(v) => `${v}%`} tick={{ fill: 'var(--muted)', fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: 'var(--surface-2)' }} contentStyle={{ background: 'var(--surface)', color: 'var(--fg)', border: '1px solid var(--line)', borderRadius: 12 }}
            formatter={(value) => [`${value} %`, 'Ocupación']} />
          <ReferenceLine y={100} stroke="var(--warn)" strokeDasharray="4 4" />
          <Bar dataKey="occupancy" radius={[4, 4, 0, 0]} maxBarSize={22} isAnimationActive={!reduced}>
            {data.map((row) => <Cell key={row.hour} fill={row.hour === first ? '#3c69ce' : row.hour === second ? '#88a53d' : 'var(--brand)'} fillOpacity={row.hour === first || row.hour === second ? 1 : 0.3} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
    <details className="mt-4 border-t border-line pt-3">
      <summary className="mb-3 cursor-pointer text-sm font-semibold text-brand">Ver tabla de las 24 horas</summary>
      <DataTable rows={data} title="Ocupación por hora" columns={[
        { id: 'hora', label: 'Hora (Lima)', value: (r) => r.hour },
        { id: 'ocupacion', label: 'Ocupación (%)', value: (r) => r.occupancy },
      ]} />
    </details>
  </div>;
}
