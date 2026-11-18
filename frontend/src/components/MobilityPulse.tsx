'use client';

import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, BarChart3, Rotate3D } from 'lucide-react';
import styles from './MobilityPulse.module.css';

type Session = { sistema: string; fecha_hora_lima: string; recomendacion_vista: boolean };
const SYSTEMS = [ ['todos', 'Todos'], ['metro_l1', 'Metro L1'], ['metropolitano', 'Metropolitano'], ['corredores', 'Corredores'], ['alimentadores', 'Alimentadores'] ];

/** Los valores siempre se calculan del mismo archivo que utiliza el laboratorio. */
export default function MobilityPulse() {
  const [rows, setRows] = useState<Session[]>([]);
  const [status, setStatus] = useState('Cargando el escenario…');
  const [system, setSystem] = useState('todos');
  const [depth, setDepth] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/simulacion/urbansafe_simulacion_600.json', { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => {
        if (!Array.isArray(data) || !data.every(r => typeof r.sistema === 'string' && typeof r.fecha_hora_lima === 'string' && Number.isFinite(Number(r.fecha_hora_lima.slice(11, 13))))) throw new Error();
        setRows(data); setStatus('');
      }).catch(e => { if (e.name !== 'AbortError') setStatus('No se pudo cargar el escenario. Puedes abrir el tablero e intentarlo de nuevo.'); });
    return () => controller.abort();
  }, []);
  const filtered = useMemo(() => rows.filter(r => system === 'todos' || r.sistema === system), [rows, system]);
  const hours = useMemo(() => Array.from({ length: 24 }, (_, hour) => ({ hour, total: filtered.filter(r => Number(r.fecha_hora_lima.slice(11, 13)) === hour).length })).filter(h => h.total > 0), [filtered]);
  const max = Math.max(1, ...hours.map(h => h.total));
  const seen = filtered.filter(r => r.recomendacion_vista).length;
  const hour = hours.find(h => h.hour === selected);
  return <section className={styles.section} id="pulso" aria-labelledby="pulso-title">
    <div className={styles.intro}>
      <span className={styles.kicker}><BarChart3 size={17} /> Laboratorio de movilidad</span>
      <h2 id="pulso-title">El ritmo de la ciudad,<br /><em>a la vista.</em></h2>
      <p>Explora las consultas por hora. Cambia de sistema y descubre cómo se mueve este escenario.</p>
      <a href="/dashboard">Abrir el panel completo</a>
      <small>Datos sintéticos de demostración · 14 oct. – 12 nov. 2026. No representan tráfico ni pasajeros en vivo.</small>
    </div>
    <div className={styles.panel}>
      <div className={styles.top}><div><span>Consultas por hora</span><strong>{filtered.length.toLocaleString('es-PE')} <small>sesiones simuladas</small></strong></div><button type="button" onClick={() => setDepth(!depth)} aria-pressed={depth} title="Cambiar profundidad del gráfico"><Rotate3D size={17} /> {depth ? 'Vista 3D' : 'Vista plana'}</button></div>
      <div className={styles.filters} aria-label="Filtrar sistema">{SYSTEMS.map(([key, label]) => <button type="button" key={key} aria-pressed={system === key} onClick={() => { setSystem(key); setSelected(null); }}>{label}</button>)}</div>
      {status ? <p role="status" className={styles.status}>{status}</p> : <>
        <div className={`${styles.chart} ${depth ? styles.depth : ''}`} role="group" aria-label="Gráfico de consultas por hora; selecciona una barra para ver su valor">
          {hours.map(h => <button type="button" key={h.hour} className={styles.column} style={{ '--bar-height': `${Math.max(3, h.total / max * 100)}%` } as React.CSSProperties} onClick={() => setSelected(h.hour)} onMouseEnter={() => setSelected(h.hour)} onFocus={() => setSelected(h.hour)} aria-label={`${h.hour}:00, ${h.total} consultas simuladas`} aria-pressed={selected === h.hour}><span className={styles.value}>{h.total}</span><span className={styles.bar} /><span className={styles.hour}>{h.hour}h</span></button>)}
        </div>
        <div className={styles.caption} aria-live="polite">{hour ? <><strong>{hour.hour}:00 – {hour.hour}:59</strong><span>{hour.total} consultas · {filtered.length ? (hour.total / filtered.length * 100).toFixed(1) : '0'}% de la selección</span></> : <><strong>Selecciona una barra</strong><span>Los valores corresponden al total del período.</span></>}</div>
        <div className={styles.metrics}><div><span>Recomendaciones vistas</span><strong>{seen}</strong></div><div><span>Sobre las consultas</span><strong>{filtered.length ? (seen / filtered.length * 100).toFixed(1) : '0'}<small>%</small></strong></div><div><span>Origen del escenario</span><strong className={styles.label}>Simulación</strong></div></div>
      </>}
    </div>
  </section>;
}
