'use client';

import { useId, useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, Clock3, TrainFront } from 'lucide-react';
import { etiquetaClase, etiquetaRecomendacion } from '@/lib/aforo';
import caso from './lima-transit-case.json';
import styles from './LimaTransitShowcase.module.css';

const estaciones = [
  { nombre: 'Villa El Salvador', x: 0.9, y: 8.3 },
  { nombre: 'Parque Industrial', x: 2.4, y: 7.0 },
  { nombre: 'Pumacahua', x: 4.3, y: 5.9 },
  { nombre: 'Villa María', x: 6.5, y: 4.7 },
  { nombre: 'María Auxiliadora', x: 8.7, y: 2.1 },
];
const edificios = [
  [1.1, 2.2, 0.8, 33], [2.3, 1.7, 0.7, 43], [3.5, 1.1, 0.9, 55],
  [4.7, 1.5, 0.8, 32], [5.9, 1.5, 1, 48], [7.2, 1.0, 0.8, 38],
  [1.4, 4.4, 0.8, 29], [2.7, 3.9, 0.9, 42], [3.9, 3.0, 0.65, 24],
  [5.2, 3.1, 0.85, 35], [6.5, 2.7, 0.65, 44], [8.4, 0.7, 0.85, 47],
  [1.0, 6.5, 0.75, 26], [2.0, 5.3, 0.7, 21], [3.2, 5.0, 0.8, 33],
  [4.5, 7.3, 0.8, 29], [5.8, 6.6, 0.65, 23], [7.1, 6.1, 0.8, 41],
  [8.3, 4.4, 0.8, 31], [9.0, 5.7, 0.64, 38], [2.0, 9.1, 0.66, 22],
  [3.4, 8.4, 0.9, 32], [6.7, 8.0, 0.7, 23], [8.0, 7.3, 0.85, 33],
].sort(([x1, y1], [x2, y2]) => x1 + y1 - x2 - y2);
const atajos = ['07:00', '18:00', '02:00'];
const numero = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 });
const porcentaje = new Intl.NumberFormat('es-ES', { style: 'percent', maximumFractionDigits: 1 });

function punto(x: number, y: number, alto = 0) {
  return [340 + (x - y) * 30, 69 + (x + y) * 12.5 - alto];
}

function poligono(puntos: number[][]) {
  return puntos.map((p) => p.join(',')).join(' ');
}

function volumen(x: number, y: number, lado: number, alto: number) {
  const a = punto(x, y), b = punto(x + lado, y), c = punto(x + lado, y + lado), d = punto(x, y + lado);
  const arriba = ([px, py]: number[]) => [px, py - alto];
  return {
    techo: poligono([a, b, c, d].map(arriba)),
    este: poligono([arriba(b), arriba(c), c, b]),
    sur: poligono([arriba(c), arriba(d), d, c]),
  };
}

function Plano({ color, servicio }: { color: string; servicio: boolean }) {
  const id = useId().replace(/:/g, '');
  const paradas = estaciones.map(({ x, y }) => punto(x, y, 14));
  const base = volumen(0, 0, 10, -13);
  const trenX = (paradas[0][0] + paradas[1][0]) / 2;
  const trenY = (paradas[0][1] + paradas[1][1]) / 2;
  return (
    <svg className={styles.scene} viewBox="0 0 680 350" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id={`${id}-luz`} cx="50%" cy="48%" r="60%">
          <stop stopColor="#22495b" />
          <stop offset="1" stopColor="#101d2b" />
        </radialGradient>
        <linearGradient id={`${id}-techo`} x2="0" y2="1">
          <stop stopColor="#668e98" />
          <stop offset="1" stopColor="#466b7d" />
        </linearGradient>
      </defs>
      <ellipse cx="340" cy="283" rx="266" ry="44" fill="#0b1823" opacity=".75" />
      <polygon points={base.este} fill="#132936" />
      <polygon points={base.sur} fill="#183542" />
      <polygon points={poligono([punto(0, 0), punto(10, 0), punto(10, 10), punto(0, 10)])} fill={`url(#${id}-luz)`} stroke="#345968" />
      {Array.from({ length: 9 }, (_, indice) => indice + 1).map((n) => (
        <g key={n} stroke="#709aa5" strokeOpacity=".23">
          <polyline points={poligono([punto(n, 0), punto(n, 10)])} />
          <polyline points={poligono([punto(0, n), punto(10, n)])} />
        </g>
      ))}
      {edificios.map(([x, y, lado, alto]) => {
        const formas = volumen(x, y, lado, alto);
        const [px, py] = punto(x + lado * 0.74, y + lado, alto - 9);
        return (
          <g key={`${x}-${y}`}>
            <polygon points={formas.este} fill="#2d5261" />
            <polygon points={formas.sur} fill="#3e6573" />
            <polygon points={formas.techo} fill={`url(#${id}-techo)`} stroke="#87a3a5" strokeWidth=".7" />
            <path d={`M${px - 8},${py - 3} l8,3.2 m-8,2.8 l8,3.2 m-8,2.8 l8,3.2`} stroke="#e7d8a2" strokeWidth="1" opacity=".72" />
          </g>
        );
      })}
      {estaciones.map(({ x, y, nombre }) => (
        <polyline key={nombre} points={poligono([punto(x, y), punto(x, y, 14)])} stroke="#77929c" strokeWidth="2" />
      ))}
      <polyline points={poligono(paradas)} fill="none" stroke="#0b151e" strokeWidth="17" strokeLinecap="round" strokeLinejoin="round" />
      <polyline className={styles.routeGlow} points={poligono(paradas)} fill="none" stroke={color} strokeWidth="12" strokeOpacity=".22" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={poligono(paradas)} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={servicio ? undefined : '8 7'} />
      {servicio && (
        <g transform={`translate(${trenX},${trenY - 8}) rotate(-3)`}>
          <rect x="-18" y="-9" width="36" height="17" rx="4" fill="#e9f4f0" stroke="#152e42" strokeWidth="1.3" />
          <rect x="-13" y="-6" width="24" height="7" rx="2" fill="#29445a" />
          <path d="M-17 4 H17" stroke={color} strokeWidth="2" />
        </g>
      )}
      {paradas.map(([x, y], indice) => (
        <g key={estaciones[indice].nombre} transform={`translate(${x},${y})`}>
          {indice === 0 && <circle r="25" fill={color} opacity=".18" />}
          <circle r={indice === 0 ? 14 : 11} fill={indice === 0 ? color : '#112333'} stroke={color} strokeWidth="1.5" />
          <text y="4" textAnchor="middle" fontSize="12" fontWeight="700" fill={indice === 0 ? '#142333' : '#eef7f1'}>{indice + 1}</text>
        </g>
      ))}
    </svg>
  );
}

export default function LimaTransitShowcase() {
  const [hora, setHora] = useState('07:00');
  const fila = caso.horas.find((item) => item.hora === hora) ?? caso.horas[0];
  const servicio = fila.ocupacion !== null && fila.clase !== 'Sin_servicio';
  const color = !servicio ? '#96a5ad' : fila.clase === 'De_pie' || fila.clase === 'Saturado' ? '#ffc97a' : '#cce987';
  const maximo = Math.max(1, ...caso.horas.map((item) => item.ocupacion ?? 0));
  const identificador = useId();
  return (
    <div className={styles.showcase}>
      <div className={styles.panel}>
        <div className={styles.line}><TrainFront size={16} aria-hidden /> Línea 1 · Lima Sur</div>
        <h3>Villa El Salvador</h3>
        <p className={styles.context}>17 de noviembre de 2025 · hacia Bayóvar</p>
        <label className={styles.selectLabel} htmlFor={identificador}>Hora de salida</label>
        <div className={styles.shortcuts} aria-label="Horarios de ejemplo" role="group">
          {atajos.map((opcion) => (
            <button key={opcion} type="button" aria-pressed={hora === opcion} onClick={() => setHora(opcion)}>
              {opcion}
            </button>
          ))}
        </div>
        <select id={identificador} value={hora} onChange={(e) => setHora(e.target.value)} className={styles.select}>
          {caso.horas.map((item) => <option key={item.hora} value={item.hora}>{item.hora}</option>)}
        </select>
        <div className={styles.result} aria-live="polite" aria-atomic="true">
          <span className={styles.state} style={{ '--estado': color } as React.CSSProperties}>{etiquetaClase(fila.clase)}</span>
          <dl className={styles.metrics}>
            <div><dt>Ocupación estimada</dt><dd>{servicio && fila.ocupacion !== null ? porcentaje.format(fila.ocupacion) : '—'}</dd></div>
            <div><dt>Espera estimada</dt><dd>{servicio && fila.espera !== null ? `${numero.format(fila.espera)} min` : '—'}</dd></div>
          </dl>
          <p className={styles.decision}><Clock3 size={15} aria-hidden /> {etiquetaRecomendacion(fila.recomendacion)}</p>
        </div>
        <p className={styles.small}>Escenario del modelo LightGBM con validaciones ATU de 2025. La estimación corresponde a la estación de salida.</p>
        <Link href="/simulacion" className={styles.full}>Simulador completo · acceso administrador <ArrowUpRight size={16} aria-hidden /></Link>
      </div>
      <figure className={styles.figure}>
        <div className={styles.figureTop}><span>Lima Sur · Línea 1</span><span>Esquema isométrico</span></div>
        <Plano color={color} servicio={servicio} />
        <div className={styles.profile}>
          <div className={styles.profileTop}><span>Ocupación por hora</span><span>00:00–23:00 · Lima</span></div>
          <div className={styles.bars} aria-hidden>
            {caso.horas.map((item) => (
              <span key={item.hora} className={item.hora === hora ? styles.barActive : undefined}
                title={`${item.hora} · ${item.ocupacion === null ? 'Fuera de horario' : porcentaje.format(item.ocupacion)}`}
                style={{ '--barra': `${Math.max(2, (item.ocupacion ?? 0) / maximo * 100)}%`, '--estado': color } as React.CSSProperties} />
            ))}
          </div>
        </div>
        <ol className={styles.stops} aria-label="Primeras cinco estaciones hacia Bayóvar">
          {estaciones.map(({ nombre }, i) => <li key={nombre}><b>{i + 1}</b><span>{nombre}</span></li>)}
        </ol>
        <figcaption>Estaciones en el orden del trazado. Edificios y distancias del esquema son ilustrativos.</figcaption>
      </figure>
    </div>
  );
}
