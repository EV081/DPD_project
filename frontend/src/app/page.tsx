import Image from 'next/image';
import Link from 'next/link';
import { ArrowDown, ArrowUpRight, ChartNoAxesCombined, ClipboardCheck, Clock3, Footprints, Plus, Route, TrainFront, BusFront, type LucideIcon } from 'lucide-react';
import { creditoFoto } from '@/lib/fotos';
import { LogoMark } from '@/components/Logo';
import { ThemeToggle } from '@/components/ThemeToggle';
import styles from './home.module.css';

type Fila = { icon: LucideIcon; title: string; text: string; detail: string; note?: string; href: string; action: string; externo?: boolean };

const PASOS: Fila[] = [
  {
    icon: ChartNoAxesCombined, title: 'Encuentra una mejor hora para salir.',
    text: 'Dinos a qué hora quieres llegar. Compara salidas y elige entre viajar con más calma o llegar con más margen.',
    detail: 'Si entras a clases a las ocho, revisa qué pasa al salir unos minutos antes: verás la espera y qué tan lleno podría ir el transporte.',
    note: 'La ocupación es una estimación; puede cambiar durante tu viaje.', href: '/simulacion', action: 'Planificar mi salida',
  },
  {
    icon: Route, title: 'Compara antes de elegir tu ruta.',
    text: 'Busca tu destino y revisa las opciones: cuánto caminarías, cuánto esperarías y cómo sería el recorrido.',
    detail: 'La opción con menos caminata no siempre te conviene. Compara dos viajes lado a lado, revisa los cambios de transporte y abre el recorrido en el mapa.',
    note: 'Cuando un tiempo o una estimación no está disponible, te lo indicamos.', href: '/destinations', action: 'Buscar mi destino',
  },
  {
    icon: Footprints, title: 'También piensa en el camino al paradero.',
    text: 'Revisa alternativas para llegar caminando y decide si prefieres un camino más corto u otro con menor riesgo estimado.',
    detail: 'El viaje empieza antes de subir. Compara cuánto caminarías con cada alternativa y decide si unos minutos adicionales encajan con tu día.',
    note: 'La información de seguridad es orientativa: ninguna ruta garantiza estar libre de incidentes.', href: '/map', action: 'Explorar el mapa',
  },
];

const FUENTES: Fila[] = [
  {
    icon: ClipboardCheck, title: 'Horarios y paradas, desde la ATU.',
    text: 'Consultamos las fichas oficiales para revisar los horarios y las paradas de cada servicio.',
    detail: 'Revisamos la información publicada para el Metropolitano, la Línea 1, los corredores y los alimentadores. Los recorridos pueden cambiar según el sentido o el horario. Las ubicaciones en el mapa también pueden apoyarse en otras fuentes.',
    href: 'https://portal.atu.gob.pe/QR/MetroLima/L1/', action: 'Consultar el portal de ATU', externo: true,
  },
  {
    icon: ChartNoAxesCombined, title: 'La ocupación se estima con datos históricos.',
    text: 'Usamos registros de viajes de la ATU de 2025 para estimar qué tan lleno podría ir el transporte.',
    detail: 'Los viajes anteriores ayudan a reconocer las horas de mayor demanda. Lo que ves es una estimación para comparar opciones; no es un conteo de pasajeros en vivo.',
    href: '', action: '',
  },
  {
    icon: Clock3, title: 'La frecuencia es una referencia.',
    text: 'Tomamos como referencia los intervalos publicados en Metrolima.info para darte una idea de cuánto podrías esperar entre servicios.',
    detail: 'Estos intervalos ayudan a calcular una espera aproximada. No son frecuencias oficiales de la ATU ni indican cuándo llegará el próximo vehículo.',
    href: 'https://metrolima.info/', action: 'Visitar metrolima.info', externo: true,
  },
];

const Filas = ({ items }: { items: Fila[] }) => (
  <div className={styles.stepList}>
    {items.map(({ icon: Icon, title, text, detail, note, href, action, externo }) => (
      <article className={styles.step} key={title}>
        <Icon size={24} strokeWidth={1.6} className={styles.stepIcon} aria-hidden="true" />
        <div>
          <h3>{title}</h3>
          <p className={styles.stepText}>{text}</p>
          <details className={styles.more}>
            <summary><span className={styles.moreClosed}>Ver más</span><span className={styles.moreOpen}>Ver menos</span><Plus size={16} aria-hidden="true" /></summary>
            <div className={styles.moreContent}>
              <p>{detail}</p>
              {note && <p className={styles.note}>{note}</p>}
              {href && (externo
                ? <a href={href} className={styles.stepLink} target="_blank" rel="noopener noreferrer"><span>{action}</span><span className="sr-only"> (abre en otra pestaña)</span></a>
                : <Link href={href} className={styles.stepLink}><span>{action}</span></Link>)}
            </div>
          </details>
        </div>
      </article>
    ))}
  </div>
);

const Foto = ({ file, alt, ratio }: { file: string; alt: string; ratio?: string }) => {
  const credito = creditoFoto(file);
  return <figure className={styles.photo} style={ratio ? { aspectRatio: ratio } : undefined}><Image src={`/imagenes/${file}`} alt={alt} fill sizes="(max-width: 850px) 100vw, 40vw" />{credito && <figcaption className={styles.credit}>{credito}</figcaption>}</figure>;
};

export default function Home() {
  return <div className={styles.page}>
    <a href="#casos" className={styles.skip}>Saltar al contenido</a>
    <main>
      <section className={styles.hero} aria-labelledby="portada-titulo">
        <Image src="/imagenes/lima-tren-manana.webp" alt="Tren elevado en un entorno urbano limeño, imagen ilustrativa" fill priority sizes="100vw" className={styles.heroPhoto} />
        <div className={styles.heroShade} aria-hidden="true" />
        <header className={styles.header}>
          <Link href="/" className={styles.brand} aria-label="UrbanSafe, inicio"><LogoMark size={32} /><span>UrbanSafe</span></Link>
          <nav className={styles.navigation} aria-label="Navegación de la portada"><a href="#casos">Cómo te ayuda</a><a href="#origen">Los datos</a></nav>
          <ThemeToggle />
          <Link href="/login" className={styles.headerAccess}>Entrar <ArrowUpRight size={16} /></Link>
        </header>
        <div className={styles.heroContent}>
          <p className={styles.eyebrow}>La ciudad se mueve. Tú eliges cómo.</p>
          <h1 id="portada-titulo">Lima cambia de ritmo.<br />Tu viaje también.</h1>
          <p className={styles.heroLead}>Elige cuándo salir y cómo llegar. Compara rutas, espera y ocupación para viajar por Lima con más información y menos dudas.</p>
          <div className={styles.heroActions}>
            <Link href="/map" className={styles.primary}>Explorar UrbanSafe <ArrowUpRight size={19} /></Link>
            <a href="#casos" className={styles.secondary}>Cómo funciona <ArrowDown size={17} /></a>
          </div>
          <p className={styles.accessNote}>Inicia sesión para planificar tu viaje.</p>
        </div>
        <small className={`${styles.credit} ${styles.heroCredit}`}>Imagen ilustrativa</small>
      </section>
      <div className={styles.systemStrip} aria-label="Sistemas de transporte disponibles"><span>Una ciudad. Más posibilidades.</span><span><TrainFront size={19} /> Metro Línea 1</span><span><BusFront size={19} /> Metropolitano</span><span><BusFront size={19} /> Corredores</span><span><Route size={19} /> Alimentadores</span></div>
      <section id="casos" className={styles.experience} aria-labelledby="casos-title">
        <div className={styles.experienceIntro}>
          <p className={styles.sectionLabel}>Cómo te ayuda</p>
          <h2 id="casos-title">Tu viaje empieza con una buena elección.</h2>
          <p>Para ir a clases, al trabajo o volver a casa: encuentra la opción que mejor se acomode a tu día.</p>
          <Link href="/map" className={styles.textLink}>Empezar mi viaje <ArrowUpRight size={17} /></Link>
          <Foto file="lima-metropolitano-real.webp" alt="Bus del Metropolitano llegando a una estación" />
        </div>
        <Filas items={PASOS} />
      </section>
      <section id="origen" className={`${styles.experience} ${styles.experienceReverse}`} aria-labelledby="origen-title">
        <div className={styles.experienceIntro}>
          <p className={styles.sectionLabel}>De dónde vienen los datos</p>
          <h2 id="origen-title">Conoce lo que hay detrás de tu viaje.</h2>
          <p>Combinamos información publicada y estimaciones para ayudarte a decidir. Aquí te contamos qué aporta cada una.</p>
        </div>
        <Filas items={FUENTES} />
      </section>
    </main>
    <footer className={styles.footer}><div><Link href="/" className={styles.brand}><LogoMark size={25} /><span>UrbanSafe<span className={styles.brandDot}>.</span></span></Link><p>Tu ciudad. Tus decisiones.</p></div><small>Un proyecto de estudiantes · UTEC</small></footer>
  </div>;
}
