import Image from 'next/image';
import Link from 'next/link';
import { ArrowDown, ArrowRight, ArrowUpRight, ChartNoAxesCombined, Footprints, Route } from 'lucide-react';
import { LogoMark } from '@/components/Logo';
import LimaTransitShowcase from '@/components/LimaTransitShowcase';
import styles from './home.module.css';

const CAPACIDADES = [
  {
    numero: '01', icono: ChartNoAxesCombined, titulo: 'La hora también cambia el viaje.',
    texto: 'Elige de dónde sales, a dónde vas y a qué hora quieres llegar. Te sugerimos cuándo salir y te mostramos la ocupación estimada del día.',
    enlace: '/simulacion', accion: 'Abrir el simulador',
  },
  {
    numero: '02', icono: Route, titulo: 'Más contexto para elegir tu ruta.',
    texto: 'Encuentra opciones hacia tu destino y compara dos recorridos: caminata, tiempo a bordo, espera y aforo, cuando esos datos están disponibles.',
    enlace: '/destinations', accion: 'Comparar destinos',
  },
  {
    numero: '03', icono: Footprints, titulo: 'El camino al paradero importa.',
    texto: 'Compara el camino más corto con una ruta segura, ponderada por denuncias históricas. Decide cuántos minutos adicionales aceptarías caminar.',
    enlace: '/destinations', accion: 'Preparar un viaje',
  },
];

export default function Home() {
  return (
    <div className={styles.page}>
      <a href="#experiencia" className={styles.skip}>Saltar al contenido</a>
      <main>
        <section className={styles.hero} aria-labelledby="portada-titulo">
          <Image src="/imagenes/lima-tren-manana.webp" alt="Imagen conceptual de un tren elevado en un entorno urbano limeño de día" fill priority sizes="100vw" className={styles.heroPhoto} />
          <div className={styles.heroShade} aria-hidden="true" />
          <header className={styles.header}>
            <Link href="/" className={styles.brand} aria-label="UrbanSafe, inicio"><LogoMark size={34} /><span>UrbanSafe</span></Link>
            <nav className={styles.navigation} aria-label="Navegación de la portada">
              <a href="#experiencia">La experiencia</a>
              <a href="#demostracion">Demostración</a>
              <a href="#datos">Los datos</a>
            </nav>
            <Link href="/login" className={styles.headerAccess}>Entrar <ArrowUpRight size={16} /></Link>
          </header>

          <div className={styles.heroContent}>
            <p className={styles.eyebrow}><span /> La ciudad se mueve. Tú eliges cómo.</p>
            <h1 id="portada-titulo">Lima cambia<br />de <em>ritmo.</em><br /><span>Tu viaje también.</span></h1>
            <p className={styles.heroLead}>Una mirada al transporte desde los datos. Explora rutas, compara horarios y entiende mejor cada tramo de tu viaje.</p>
            <div className={styles.heroActions}>
              <Link href="/map" className={styles.primary}>Explorar UrbanSafe <ArrowUpRight size={19} /></Link>
              <a href="#demostracion" className={styles.secondary}>Ver demostración <ArrowDown size={17} /></a>
            </div>
            <p className={styles.accessNote}>El mapa y los escenarios completos requieren iniciar sesión.</p>
          </div>

          <div className={styles.heroBottom}>
            <div><span className={styles.heroBottomLabel}>Transporte de Lima</span><p>Metropolitano · Línea 1 · Corredores · Alimentadores</p></div>
            <p className={styles.photoNote}>Imagen conceptual.<br />No representa una ruta real.</p>
          </div>
        </section>

        <section id="experiencia" className={styles.experience} aria-labelledby="experiencia-titulo">
          <div className={styles.experienceIntro}>
            <p className={styles.sectionLabel}>01 / La experiencia</p>
            <h2 id="experiencia-titulo">No es solo<br />llegar.<br /><em>Es elegir.</em></h2>
            <p>Del momento de salir al camino al paradero: información para mirar el viaje con más detalle.</p>
            <Link href="/map" className={styles.textLink}>Conocer la aplicación <ArrowUpRight size={17} /></Link>
          </div>
          <div className={styles.featureList}>
            {CAPACIDADES.map(({ numero, icono: Icono, titulo, texto, enlace, accion }) => (
              <article className={styles.feature} key={numero}>
                <div className={styles.featureNumber}><span>{numero}</span><Icono size={24} strokeWidth={1.4} aria-hidden="true" /></div>
                <div><h3>{titulo}</h3><p>{texto}</p><Link href={enlace} className={styles.textLink}>{accion} <ArrowRight size={16} /></Link></div>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.streetStory} aria-labelledby="camino-titulo">
          <div className={styles.streetPhoto}>
            <Image src="/imagenes/lima-camino-paradero.webp" alt="Escena ilustrativa de personas caminando hacia un paradero en Lima" fill sizes="(max-width: 767px) 100vw, 65vw" />
            <span>Imagen ilustrativa · no corresponde a una ruta calculada</span>
          </div>
          <div className={styles.streetContent}>
            <p className={styles.sectionLabel}>Del inicio al destino</p>
            <h2 id="camino-titulo">Cada tramo<br /><em>cuenta.</em></h2>
            <p>La comparación incluye el camino al paradero, la espera y el tiempo a bordo cuando existen datos para esa opción.</p>
            <Link href="/destinations" className={styles.textLink}>Comparar recorridos <ArrowUpRight size={17} /></Link>
          </div>
        </section>

        <section id="demostracion" className={styles.demo} aria-labelledby="demo-titulo">
          <div className={styles.demoHeading}>
            <div><p className={styles.sectionLabel}>02 / En movimiento</p><h2 id="demo-titulo">Mira cómo se<br /><em>conecta el viaje.</em></h2></div>
            <p>Explora esta muestra de la experiencia. Para consultar tus propios escenarios, entra a la aplicación.</p>
          </div>
          <LimaTransitShowcase />
          <div className={styles.demoFooter}><p>La demostración ayuda a entender el flujo. Revisa siempre el origen y el alcance de cada estimación.</p><Link href="/map" className={styles.textLink}>Abrir la aplicación <ArrowUpRight size={17} /></Link></div>
        </section>

        <section id="datos" className={styles.data} aria-labelledby="datos-titulo">
          <div className={styles.dataHeading}>
            <div><p className={styles.sectionLabel}>03 / La base del proyecto</p><h2 id="datos-titulo">Datos claros.<br /><em>Contexto primero.</em></h2></div>
            <div className={styles.dataYear}><strong>2025</strong><span>Base histórica ATU para el aforo</span></div>
          </div>
          <div className={styles.dataNotes}>
            <article><span>01</span><h3>Estimaciones, con origen.</h3><p>El aforo usa datos históricos de la ATU. No es un conteo de pasajeros en vivo.</p></article>
            <article><span>02</span><h3>El riesgo requiere contexto.</h3><p>Las rutas a pie se ponderan con denuncias registradas. No garantizan seguridad ni describen incidentes en tiempo real.</p></article>
            <article><span>03</span><h3>Un dato ausente se explica.</h3><p>Cuando una opción no tiene estimación disponible, se indica en la interfaz para no confundir ausencia con cero.</p></article>
          </div>
        </section>

        <section className={styles.closing} aria-labelledby="comenzar-titulo">
          <div><p className={styles.sectionLabel}>La próxima salida</p><h2 id="comenzar-titulo">Empieza por<br /><em>mirar tus opciones.</em></h2></div>
          <Link href="/map" className={styles.closingLink}>Entrar a UrbanSafe <ArrowUpRight size={28} strokeWidth={1.4} /></Link>
          <p className={styles.closingPhotoNote}>Imagen conceptual de Lima · no muestra una ruta calculada</p>
        </section>
      </main>
      <footer className={styles.footer}>
        <Link href="/" className={styles.brand}><LogoMark size={28} /><span>UrbanSafe</span></Link>
        <p>Un proyecto de estudiantes · UTEC</p>
        <a href="#portada-titulo" className={styles.backTop}>Volver arriba <ArrowUpRight size={15} /></a>
      </footer>
    </div>
  );
}
