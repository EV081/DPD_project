'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Camera, MapPin, Maximize2, X } from 'lucide-react';
import styles from './CityExplorer.module.css';

type Category = 'Todos' | 'Transporte' | 'A pie' | 'La ciudad';
type Scene = { id: string; category: Exclude<Category, 'Todos'>; title: string; place: string; image: string; alt: string; author: string; source: string; href: string; action: string; position?: string };
const CATEGORIES: Category[] = ['Todos', 'Transporte', 'A pie', 'La ciudad'];
const SCENES: Scene[] = [
  { id: 'barranco', category: 'A pie', title: 'El viaje empieza caminando.', place: 'Barranco, Lima', image: 'lima-barranco-puente-real.webp', alt: 'Puente y entorno urbano del distrito de Barranco en Lima', author: 'tadekk', source: 'https://commons.wikimedia.org/wiki/File:Barranco_District_Lima_Peru.jpg', href: '/map', action: 'Explorar el mapa' },
  { id: 'metro', category: 'Transporte', title: 'Conecta con otro ritmo.', place: 'Metro de Lima, estación La Cultura', image: 'lima-metro-lacultura-real.webp', alt: 'Vista exterior de la estación elevada La Cultura del Metro de Lima y su avenida', author: 'Carlos Felipe Pardo', source: 'https://commons.wikimedia.org/wiki/File:Lima_Peru_Electric_Train.jpg', href: '/simulacion', action: 'Planificar mi salida' },
  { id: 'metropolitano', category: 'Transporte', title: 'Tu siguiente conexión.', place: 'Metropolitano, Lima', image: 'lima-metropolitano-real.webp', alt: 'Bus articulado del Metropolitano de Lima', author: 'Carlos Felipe Pardo', source: 'https://commons.wikimedia.org/wiki/File:Lima_Peru_Metropolitano_Bus.jpg', href: '/destinations', action: 'Comparar recorridos' },
  { id: 'catedral', category: 'La ciudad', title: 'Una ciudad por redescubrir.', place: 'Catedral de Lima, Plaza Mayor', image: 'lima-catedral-real.webp', alt: 'Fachada de la Catedral de Lima junto a la Plaza Mayor', author: 'Hongbin', source: 'https://unsplash.com/photos/a-large-white-building-with-a-clock-tower-LHkxt3r_fvo', href: '/destinations', action: 'Buscar mi destino' },
  { id: 'costa', category: 'La ciudad', title: 'La ciudad también se disfruta.', place: 'Costa Verde, Lima', image: 'lima-costa-verde-real.jpg', alt: 'Vista de los acantilados, la costa y los edificios de Lima', author: 'Marc Wieland', source: 'https://unsplash.com/es/fotos/ciudad-costera-con-acantilados-que-dominan-las-olas-del-oceano-ieMzKs0_MbM', href: '/destinations', action: 'Buscar un destino' },
  { id: 'plaza-flores', category: 'Transporte', title: 'Tu conexión empieza aquí.', place: 'Estación Plaza de Flores', image: 'estacion-plaza-de-flores-real.jpg', alt: 'Estación Plaza de Flores del Metropolitano en Lima', author: 'TomasVial', source: 'https://commons.wikimedia.org/wiki/File:Estaci%C3%B3n_Plaza_de_Flores_del_Metropolitano.jpg', href: '/map', action: 'Ver estaciones' },
  { id: 'jesus-maria', category: 'La ciudad', title: 'Mira tus posibilidades.', place: 'Jesús María, Lima', image: 'lima-ciudad-aerea-real.jpg', alt: 'Vista aérea de edificios y un parque en Jesús María, Lima', author: 'Kieran Proctor', source: 'https://unsplash.com/photos/an-aerial-view-of-a-city-with-tall-buildings-rQT0D4nwcqM', href: '/destinations', action: 'Comparar recorridos' },
  { id: 'bus', category: 'Transporte', title: 'Antes de subir, compara.', place: 'Transporte público de Lima', image: 'lima-bus-calle-real.jpg', alt: 'Bus local y pasajero en una calle de Lima', author: 'Matt Rivera', source: 'https://www.pexels.com/photo/street-scene-in-lima-with-a-local-bus-35876785/', href: '/simulacion', action: 'Revisar mi salida' },
  { id: 'magdalena', category: 'La ciudad', title: 'Lima sigue en movimiento.', place: 'Magdalena del Mar, Lima', image: 'lima-magdalena-noche-real.webp', alt: 'Edificios y avenidas iluminadas de Magdalena del Mar por la noche', author: 'Kieran Proctor', source: 'https://unsplash.com/photos/a-view-of-a-city-at-night-from-the-top-of-a-building-FOLIYvTbmaI', href: '/simulacion', action: 'Revisar horarios' },
  { id: 'malecon', category: 'A pie', title: 'El primer tramo cuenta.', place: 'Malecón Cisneros, Miraflores', image: 'lima-malecon-miraflores-real.webp', alt: 'Vista aérea del malecón, parques y costa de Miraflores en Lima', author: 'Willian Justen de Vasconcellos', source: 'https://unsplash.com/photos/birds-eye-photography-of-village-beside-water-hZFXVjeS73A', href: '/map', action: 'Explorar accesos a pie' },
];

/** La galería ofrece contexto visual; las rutas se consultan en las herramientas del proyecto. */
export default function CityExplorer() {
  const [category, setCategory] = useState<Category>('Todos');
  const [selected, setSelected] = useState<Scene | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const visible = SCENES.filter(scene => category === 'Todos' || scene.category === category);
  useEffect(() => {
    const element = dialog.current;
    if (selected && element && !element.open) element.showModal();
  }, [selected]);
  const close = () => { dialog.current?.close(); setSelected(null); };
  return <section className={styles.section} id="explorar-lima" aria-labelledby="city-title">
    <div className={styles.heading}><div><p className={styles.eyebrow}><Camera size={15} /> Lima, en primera persona</p><h2 id="city-title">Hay mucho por ver.<br /><em>Elige cómo llegar.</em></h2></div><p>Una mirada real a la ciudad.<br />Explora las fotos y encuentra tu próximo paso.</p></div>
    <div className={styles.toolbar}><div className={styles.filters} role="group" aria-label="Filtrar fotografías de Lima">{CATEGORIES.map(item => <button type="button" key={item} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}</div><span className={styles.count} aria-live="polite">{visible.length} fotografías</span></div>
    <div className={styles.grid}>
      {visible.map((scene, index) => <article className={`${styles.card} ${index === 0 && category === 'Todos' ? styles.featured : ''}`} key={scene.id}>
        <button className={styles.preview} type="button" onClick={() => setSelected(scene)} aria-label={`Ampliar fotografía: ${scene.place}`}><Image src={`/imagenes/${scene.image}`} alt={scene.alt} fill sizes={index === 0 && category === 'Todos' ? '(max-width: 700px) 100vw, 66vw' : '(max-width: 430px) 100vw, (max-width: 700px) 50vw, 33vw'} loading="lazy" style={{ objectPosition: scene.position || 'center' }} /><span className={styles.zoom}><Maximize2 size={16} /><span>Ver foto</span></span></button>
        <div className={styles.copy}><p><MapPin size={13} /> {scene.place}</p><h3>{scene.title}</h3><Link href={scene.href}>{scene.action}</Link></div>
        <span className={styles.tag}>{scene.category}</span>
      </article>)}
    </div>
    {visible.length === 0 && <p className={styles.empty}>Pronto encontrarás más fotografías de esta categoría. Puedes explorar las estaciones en el mapa.</p>}
    <div className={styles.note}><p>Fotografías reales de contexto. Las opciones de viaje y sus estimaciones se consultan en la aplicación.</p><a href="/imagenes/FOTOGRAFIAS_REALES.md">Fuentes y autores <ArrowUpRight size={14} /></a></div>
    <dialog ref={dialog} className={styles.dialog} aria-labelledby="city-photo-title" onClose={() => setSelected(null)} onClick={event => { if (event.target === event.currentTarget) close(); }}>
      {selected && <div className={styles.modalContent}><button className={styles.close} type="button" onClick={close} aria-label="Cerrar fotografía"><X size={22} /></button><div className={styles.modalImage}><Image src={`/imagenes/${selected.image}`} alt={selected.alt} fill sizes="(max-width: 1000px) 94vw, 1000px" style={{ objectPosition: selected.position || 'center' }} /></div><div className={styles.modalCopy}><div><p className={styles.eyebrow}>{selected.category}</p><h3 id="city-photo-title">{selected.place}</h3><p>Fotografía de <a href={selected.source} target="_blank" rel="noopener noreferrer">{selected.author} <ArrowUpRight size={12} /></a></p></div><Link href={selected.href} onClick={close}>{selected.action} <ArrowUpRight size={18} /></Link></div></div>}
    </dialog>
  </section>;
}
