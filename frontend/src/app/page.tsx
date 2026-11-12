import Image from 'next/image';
import Link from 'next/link';
import { ArrowDown, ArrowRight, ArrowUpRight, ChartNoAxesCombined, ClipboardCheck, Clock3, Footprints, Route, Plus } from 'lucide-react';
import { LogoMark } from '@/components/Logo';
import { ThemeToggle } from '@/components/ThemeToggle';
import styles from './home.module.css';

const CAPACIDADES = [
  {
    icono: ChartNoAxesCombined, titulo: 'Encuentra una mejor hora para salir.',
    texto: 'Dinos a qué hora quieres llegar. Compara salidas y elige entre viajar con más calma o llegar con más margen.',
    detalle: 'Por ejemplo, si entras a clases a las ocho, puedes revisar qué pasa al salir unos minutos antes. Verás la espera y qué tan lleno podría ir el transporte para decidir qué horario te conviene.',
    nota: 'La ocupación es una estimación; puede cambiar durante tu viaje.',
    enlace: '/simulacion', accion: 'Planificar mi salida',
  },
  {
    icono: Route, titulo: 'Compara antes de elegir tu ruta.',
    texto: 'Busca tu destino y revisa las opciones: cuánto caminarías, cuánto esperarías y cómo sería el recorrido.',
    detalle: 'No siempre la opción con menos caminata es la que más te conviene. Puedes comparar dos viajes lado a lado, revisar los cambios de transporte y abrir el recorrido que prefieras en el mapa.',
    nota: 'Cuando un tiempo o una estimación no está disponible, te lo indicamos.',
    enlace: '/destinations', accion: 'Buscar mi destino',
  },
  {
    icono: Footprints, titulo: 'También piensa en el camino al paradero.',
    texto: 'Revisa alternativas para llegar caminando y decide si prefieres un camino más corto u otro con menor riesgo estimado.',
    detalle: 'El viaje empieza antes de subir. UrbanSafe te permite comparar cuánto caminarías con cada alternativa y decidir si unos minutos adicionales encajan con tu día.',
    nota: 'La información de seguridad es orientativa: ninguna ruta garantiza estar libre de incidentes.',
    enlace: '/map', accion: 'Explorar el mapa',
  },
];

const FUENTES = [
  {
    icono: ClipboardCheck, titulo: 'Horarios y paradas, desde la ATU.',
    texto: 'Consultamos las fichas oficiales para revisar los horarios y las paradas de cada servicio.',
    detalle: 'Revisamos la información publicada para el Metropolitano, la Línea 1, los corredores y los alimentadores. Los recorridos pueden cambiar según el sentido o el horario. Las ubicaciones en el mapa también pueden apoyarse en otras fuentes.',
    enlace: 'https://portal.atu.gob.pe/QR/MetroLima/L1/', accion: 'Consultar el portal de ATU',
  },
  {
    icono: ChartNoAxesCombined, titulo: 'La ocupación se estima con datos históricos.',
    texto: 'Usamos registros de viajes de la ATU de 2025 para estimar qué tan lleno podría ir el transporte.',
    detalle: 'Los viajes anteriores ayudan a reconocer las horas de mayor demanda. Lo que ves es una estimación para comparar opciones; no es un conteo de pasajeros en vivo.',
  },
  {
    icono: Clock3, titulo: 'La frecuencia es una referencia.',
    texto: 'Los intervalos entre servicios se apoyan en metrolima.info y en ajustes del proyecto.',
    detalle: 'Estos intervalos ayudan a calcular una espera aproximada. No son frecuencias oficiales de la ATU ni indican cuándo llegará el próximo vehículo.',
    enlace: 'https://metrolima.info/', accion: 'Visitar metrolima.info',
  },
];

export default function Home() {
  return (
    <div className={styles.page}>
      <a href="#experiencia" className={styles.skip}>Saltar al contenido</a>
      <main>
        <section className={styles.hero} aria-labelledby="portada-titulo">
          <Image src="/imagenes/lima-tren-manana.webp" alt="Tren elevado en un entorno urbano limeño, imagen ilustrativa" fill priority sizes="100vw" className={styles.heroPhoto} />
          <div className={styles.heroShade} aria-hidden="true" />
          <header className={styles.header}>
            <Link href="/" className={styles.brand} aria-label="UrbanSafe, inicio"><LogoMark size={32} /><span>UrbanSafe</span></Link>
            <nav className={styles.navigation} aria-label="Navegación de la portada"><a href="#experiencia">Cómo te ayuda</a><a href="#fuentes">Los datos</a></nav>
            <ThemeToggle />
            <Link href="/login" className={styles.headerAccess}>Entrar <ArrowUpRight size={16} /></Link>
          </header>
          <div className={styles.heroContent}>
            <p className={styles.eyebrow}>La ciudad se mueve. Tú eliges cómo.</p>
            <h1 id="portada-titulo">Lima cambia de ritmo.<br />Tu viaje también.</h1>
            <p className={styles.heroLead}>Elige cuándo salir y cómo llegar. Compara rutas, espera y ocupación para viajar por Lima con más información y menos dudas.</p>
            <div className={styles.heroActions}>
              <Link href="/map" className={styles.primary}>Explorar UrbanSafe <ArrowUpRight size={19} /></Link>
              <a href="#experiencia" className={styles.secondary}>Cómo funciona <ArrowDown size={17} /></a>
            </div>
            <p className={styles.accessNote}>Inicia sesión para planificar tu viaje.</p>
          </div>
        </section>
        <section id="experiencia" className={styles.experience} aria-labelledby="experiencia-titulo">
          <div className={styles.experienceIntro}>
            <p className={styles.sectionLabel}>Cómo te ayuda</p>
            <h2 id="experiencia-titulo">Tu viaje empieza con una buena elección.</h2>
            <p>Para ir a clases, al trabajo o volver a casa: encuentra la opción que mejor se acomode a tu día.</p>
            <Link href="/map" className={styles.textLink}>Empezar mi viaje <ArrowUpRight size={17} /></Link>
          </div>
          <div className={styles.featureList}>
            {CAPACIDADES.map(({ icono: Icono, titulo, texto, detalle, nota, enlace, accion }) => (
              <article className={styles.feature} key={titulo}>
                <Icono size={23} strokeWidth={1.6} className={styles.featureIcon} aria-hidden="true" />
                <div>
                  <h3>{titulo}</h3><p>{texto}</p>
                  <details className={styles.more}>
                    <summary><span className={styles.moreClosed}>Ver más</span><span className={styles.moreOpen}>Ver menos</span><Plus size={16} aria-hidden="true" /></summary>
                    <div className={styles.moreContent}><p>{detalle}</p><p className={styles.note}>{nota}</p><Link href={enlace} className={styles.textLink}>{accion} <ArrowRight size={16} /></Link></div>
                  </details>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section id="fuentes" className={`${styles.experience} ${styles.sources}`} aria-labelledby="fuentes-titulo">
          <div className={styles.experienceIntro}>
            <p className={styles.sectionLabel}>De dónde vienen los datos</p>
            <h2 id="fuentes-titulo">Conoce lo que hay detrás de tu viaje.</h2>
            <p>Combinamos información publicada y estimaciones para ayudarte a decidir. Aquí te contamos qué aporta cada una.</p>
          </div>
          <div className={styles.featureList}>
            {FUENTES.map(({ icono: Icono, titulo, texto, detalle, enlace, accion }) => (
              <article className={styles.feature} key={titulo}>
                <Icono size={23} strokeWidth={1.6} className={styles.featureIcon} aria-hidden="true" />
                <div>
                  <h3>{titulo}</h3><p>{texto}</p>
                  <details className={styles.more}>
                    <summary><span className={styles.moreClosed}>Ver más</span><span className={styles.moreOpen}>Ver menos</span><Plus size={16} aria-hidden="true" /></summary>
                    <div className={styles.moreContent}>
                      <p>{detalle}</p>
                      {enlace && <a href={enlace} className={styles.textLink} target="_blank" rel="noopener noreferrer">{accion}<ArrowUpRight size={16} aria-hidden="true" /><span className="sr-only"> (abre en otra pestaña)</span></a>}
                    </div>
                  </details>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
      <footer className={styles.footer}>
        <Link href="/" className={styles.brand}><LogoMark size={26} /><span>UrbanSafe</span></Link>
        <p>Un proyecto de estudiantes · UTEC</p>
        <a href="#portada-titulo" className={styles.backTop}>Volver arriba <ArrowUpRight size={15} /></a>
      </footer>
    </div>
  );
}
