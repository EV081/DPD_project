// Ruta de bus animada (SVG): un vehículo recorre la línea, se detiene en cada parada y el tramo
// recorrido se resalta. Con «reducir movimiento» queda una imagen fija con el bus en una parada.

const RUTA = 'M40 215 C140 215 170 105 270 105 S390 205 500 200 S640 95 760 95';

// Posición de cada parada en la curva (fracciones 0, 0,2 … 1 de su longitud), arriba o abajo de la línea
const PARADAS = [
  { x: 40, y: 215, nombre: 'Matellini', arriba: false },
  { x: 178, y: 141, nombre: 'Benavides', arriba: true },
  { x: 327.6, y: 118, nombre: 'Angamos', arriba: true },
  { x: 465, y: 197.8, nombre: 'Javier Prado', arriba: false },
  { x: 614.4, y: 154, nombre: 'Estación Central', arriba: false },
  { x: 760, y: 95, nombre: 'Naranjal', arriba: true },
];

// Se detiene un momento en cada parada y avanza a velocidad constante entre ellas
const TIEMPOS = '0;.04;.192;.232;.384;.424;.576;.616;.768;.808;.96;1';
const PUNTOS = '0;0;.2;.2;.4;.4;.6;.6;.8;.8;1;1';
const RESTANTE = '1;1;.8;.8;.6;.6;.4;.4;.2;.2;0;0';
const DURACION = '16s';

export default function RutaAnimada({ className = '' }: { className?: string }) {
  return (
    <figure className={`ruta-animada ${className}`}>
      <svg viewBox="0 0 800 300" preserveAspectRatio="xMidYMid meet" role="img"
        aria-label="Animación: un bus recorre una ruta y se detiene en cada parada">
        <g className="ruta-calles" aria-hidden>
          {[60, 140, 220, 300].map((y) => <line key={`h${y}`} x1="0" x2="800" y1={y - 20} y2={y + 10} />)}
          {[90, 230, 370, 520, 660].map((x) => <line key={`v${x}`} x1={x} x2={x + 40} y1="0" y2="300" />)}
        </g>

        <path d={RUTA} className="ruta-base" />
        <path d={RUTA} className="ruta-recorrida ruta-movil" pathLength={1} strokeDasharray="1 1">
          <animate attributeName="stroke-dashoffset" values={RESTANTE} keyTimes={TIEMPOS} dur={DURACION} repeatCount="indefinite" />
        </path>
        <path d={RUTA} className="ruta-recorrida ruta-fija" pathLength={1} strokeDasharray="0.4 1" />

        {PARADAS.map((p, i) => (
          <g key={p.nombre}>
            <circle cx={p.x} cy={p.y} r={i === 0 || i === PARADAS.length - 1 ? 11 : 8} className="ruta-parada" />
            <text x={p.x} y={p.arriba ? p.y - 26 : p.y + 36} textAnchor={i === 0 ? 'start' : i === PARADAS.length - 1 ? 'end' : 'middle'}
              className="ruta-etiqueta">{p.nombre}</text>
          </g>
        ))}

        <g className="ruta-bus ruta-movil">
          <animateMotion path={RUTA} keyPoints={PUNTOS} keyTimes={TIEMPOS} calcMode="linear" dur={DURACION}
            repeatCount="indefinite" rotate="auto" />
          <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.02;.97;1" dur={DURACION} repeatCount="indefinite" />
          <Bus />
        </g>
        <g className="ruta-bus ruta-fija" transform="translate(327.6 118)"><Bus /></g>
      </svg>
    </figure>
  );
}

function Bus() {
  return (
    <g transform="translate(-26 -11)">
      <rect width="52" height="22" rx="7" className="ruta-bus-cuerpo" />
      {[8, 20, 32].map((x) => <rect key={x} x={x} y="5" width="9" height="7" rx="1.5" className="ruta-bus-ventana" />)}
      <rect x="44" y="5" width="5" height="12" rx="1.5" className="ruta-bus-ventana" />
    </g>
  );
}
