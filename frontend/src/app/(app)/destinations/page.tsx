'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, Map, Bus, ChevronRight, TriangleAlert, Footprints, Lightbulb, Repeat2, Check } from 'lucide-react';
import SearchAutocomplete from '@/components/SearchAutocomplete';
import SystemBadge from '@/components/SystemBadge';
import TripComparison, { RouteMetrics } from '@/components/TripComparison';
import { ForecastScopeNote } from '@/components/ForecastPanel';
import { comparedRoutes, ROUTE_PAGE_SIZE, tripRouteKey, tripRouteLabel, routeServiceLabel } from '@/lib/trip-comparison';
import { Skeleton, EmptyState } from '@/components/Spinner';
import { matchTrip } from '@/lib/services';
import { opcionesDeViaje } from '@/lib/aforo';
import { getUserLocation, LIMA_CENTER, Coords } from '@/lib/geolocation';
import { createRequestGate } from '@/lib/ui-state';
import { TRIP_STORAGE_KEY } from '@/lib/constants';
import { TripMatchResponse, AutocompleteSuggestion, MatchedRoute } from '@/lib/types';

export default function DestinationsPage() {
  const router = useRouter();
  const [location, setLocation] = useState<Coords | null>(null);
  const [locationFallback, setLocationFallback] = useState(false);
  const [tripData, setTripData] = useState<TripMatchResponse | null>(null);
  const [tripOriginIsReference, setTripOriginIsReference] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [locationNote, setLocationNote] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(ROUTE_PAGE_SIZE);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const requests = useRef(createRequestGate());
  useEffect(() => () => requests.current.cancel(), []);

  useEffect(() => {
    getUserLocation()
      .then(setLocation)
      .catch(() => {
        setLocation(LIMA_CENTER);
        setLocationFallback(true);
        setLocationNote('Sin acceso a tu ubicación: se usa el centro de Lima como punto de partida.');
      });
  }, []);

  const search = async (input: string | AutocompleteSuggestion) => {
    const vigente = requests.current.begin();
    const origin = location ?? LIMA_CENTER;
    setLocationNote(!location ? 'La ubicación aún no está disponible: esta búsqueda parte del centro de Lima.'
      : locationFallback ? 'Sin acceso a tu ubicación: esta búsqueda parte del centro de Lima.' : null);
    setLoading(true);
    setMessage(null);
    setTripData(null);
    setVisibleCount(ROUTE_PAGE_SIZE);
    setSelectedKeys([]);
    try {
      const dest = typeof input === 'string' ? input : { lat: input.lat, lon: input.lon };
      const respuesta = await matchTrip(origin.lat, origin.lon, dest);
      if (!vigente()) return;
      // Con coordenadas el backend no sabe cómo se llama el lugar: se usa el nombre que eligió la persona
      const response = typeof input === 'string' ? respuesta
        : { ...respuesta, destination: { ...respuesta.destination, resolved_name: input.display_name } };
      setTripData(response);
      setTripOriginIsReference(!location || locationFallback);
      if (opcionesDeViaje(response).rutas.length === 0) {
        setMessage('No se encontraron rutas a este destino, ni directas ni con un transbordo, dentro del radio de búsqueda.');
      }
    } catch (error) {
      if (!vigente()) return;
      console.error('Error al planificar el viaje:', error);
      setMessage('Ocurrió un error al buscar rutas hacia tu destino. Inténtalo de nuevo.');
    } finally {
      if (vigente()) setLoading(false);
    }
  };

  const { rutas: routes, conTransbordo } = tripData ? opcionesDeViaje(tripData) : { rutas: [], conTransbordo: false };

  const shownRoutes = routes.slice(0, visibleCount);
  const comparison = comparedRoutes(routes, selectedKeys);
  const toggleCompare = (route: MatchedRoute) => {
    const key = tripRouteKey(route);
    setSelectedKeys((current) => current.includes(key)
      ? current.filter((selected) => selected !== key)
      : current.length < 2 ? [...current, key] : current);
  };
  const openRoute = (route: MatchedRoute) => {
    if (!tripData) return;
    try {
      sessionStorage.setItem(TRIP_STORAGE_KEY, JSON.stringify({ selectedRoute: route, destination: tripData.destination, origin: tripData.origin, originIsReference: tripOriginIsReference }));
      router.push('/map');
    } catch {
      setMessage('No pudimos guardar la selección para abrir el mapa. Revisa el almacenamiento del navegador e inténtalo otra vez.');
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-10">
      <header className="hero p-6 md:p-8">
        <div className="pointer-events-none absolute -right-10 -top-16 h-56 w-56 rounded-full bg-sky-400/30 blur-3xl" />
        <h1 className="relative text-3xl font-bold tracking-tight">¿A dónde vas hoy?</h1>
        <p className="relative mt-1.5 max-w-xl text-sm text-blue-100/90">Revisa unas pocas opciones, compara su espera y aforo, y abre la que prefieras en el mapa.</p>
      </header>

      <SearchAutocomplete className="relative z-20 mt-6" placeholder="¿A qué lugar o avenida te diriges?"
        onSelectDestination={search} onSearchSubmit={search} />
      {locationNote && <p className="mt-2 text-xs text-muted">{locationNote}</p>}

      {loading && (
        <div className="mt-8 grid gap-4 lg:grid-cols-2" role="status" aria-label="Buscando rutas">
          <Skeleton className="h-52 !rounded-2xl" /><Skeleton className="h-52 !rounded-2xl" />
        </div>
      )}

      {!loading && message && (
        <p role="status" className="mt-8 flex items-start gap-3 rounded-xl bg-warn/12 px-4 py-3 text-sm text-warn">
          <TriangleAlert size={18} className="mt-0.5 shrink-0" /> {message}
        </p>
      )}

      {!loading && tripData && routes.length > 0 && (
        <section className="mt-8" aria-label="Resultados">
          <div className="card flex flex-wrap items-center gap-3 p-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-danger/12 text-danger">
              <MapPin size={19} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="eyebrow">Destino</p>
              <p className="break-words font-semibold text-fg">{tripData.destination.resolved_name}</p>
            </div>
            <span className="shrink-0 rounded-full bg-brand-soft px-3 py-1 text-sm font-semibold text-brand">
              {shownRoutes.length} de {routes.length} opciones
            </span>
          </div>

          <p className="mt-3 text-sm text-muted">Mantenemos el orden del cálculo del servidor. Puedes comparar hasta dos opciones; mostrar más no cambia tu selección.</p>
          <ForecastScopeNote />
          {conTransbordo && (
            <p className="mt-3 flex gap-2.5 rounded-xl bg-surface-2 px-4 py-3 text-sm text-muted">
              <Repeat2 size={17} className="mt-0.5 shrink-0" />
              No hay ruta directa a este destino. Estas opciones usan un transbordo; los tiempos son estimados.
            </p>
          )}

          {tripData.recomendacion_viaje?.mensaje && (
            <p className="mt-3 flex gap-2.5 rounded-xl bg-ok/12 px-4 py-3 text-sm text-ok">
              <Lightbulb size={17} className="mt-0.5 shrink-0" /> {tripData.recomendacion_viaje.mensaje}
            </p>
          )}

          <TripComparison routes={comparison} onOpen={openRoute} onRemove={toggleCompare} onClear={() => setSelectedKeys([])} />
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            {shownRoutes.map((item, index) => {
              const key = tripRouteKey(item);
              const selected = selectedKeys.includes(key);
              const walkTo = Math.round(item.origin_walk_m);
              const walkFrom = Math.round(item.dest_walk_m);
              const best = index === 0;
              return (
                <article
                  key={key}
                  className={`card group relative min-w-0 p-5 text-left ${best ? '!border-brand ring-1 ring-brand/30' : ''}`}
                >
                  {best && (
                    <span className="absolute -top-2.5 left-4 rounded-full bg-brand px-2.5 py-0.5 text-xs font-semibold text-white dark:text-[#06101f]">
                      Primera opción del sistema
                    </span>
                  )}
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <SystemBadge system={item.system} />
                        {routeServiceLabel(item) && <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs font-semibold text-fg">{routeServiceLabel(item)}</span>}
                      </div>
                      {item.transbordo && <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-brand-soft px-2 py-0.5 text-xs font-semibold text-brand"><Repeat2 size={12} /> 1 transbordo</span>}
                      <p className="mt-2.5 text-base font-semibold text-fg">Sube en {item.boarding_station}</p>
                    </div>
                    <ChevronRight size={18} className="mt-1 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand" />
                  </div>

                  <ul className="mt-4 space-y-2 text-sm text-muted">
                    <li className="flex items-center gap-2.5"><Footprints size={16} className="shrink-0" /> {walkTo} m caminando hasta el paradero</li>
                    {item.transbordo ? (
                      <>
                        <li className="flex items-center gap-2.5"><Bus size={16} className="shrink-0" /> Bájate en <b className="font-semibold text-fg">{item.leaving_station}</b> y camina {Math.round(item.transbordo.caminata_m)} m</li>
                        <li className="flex items-start gap-2.5"><Repeat2 size={16} className="mt-0.5 shrink-0" /> <span>Sube en <b className="font-semibold text-fg">{item.transbordo.boarding_station}</b> ({item.transbordo.system === 'metropolitano' ? 'Metropolitano' : `Ruta ${item.transbordo.route_code}`}) y bájate en <b className="font-semibold text-fg">{item.transbordo.leaving_station}</b> · {walkFrom} m al destino</span></li>
                      </>
                    ) : (
                      <li className="flex items-center gap-2.5"><Bus size={16} className="shrink-0" /> Bájate en <b className="font-semibold text-fg">{item.leaving_station}</b> · {walkFrom} m al destino</li>
                    )}
                  </ul>

                  <RouteMetrics route={item} />
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button className="btn btn-primary flex-1" onClick={() => openRoute(item)} aria-label={`Ver en mapa: ${tripRouteLabel(item)}`}>Ver en mapa <ChevronRight size={16} /></button>
                    <button className={`btn ${selected ? 'btn-primary' : 'btn-secondary'}`} aria-pressed={selected} aria-label={`${selected ? 'Quitar de comparación' : 'Comparar'}: ${tripRouteLabel(item)}`} disabled={!selected && selectedKeys.length === 2} onClick={() => toggleCompare(item)}>{selected && <Check size={15} />}{selected ? 'Seleccionada' : 'Comparar'}</button>
                  </div>
                </article>
              );
            })}
          </div>
          <div className="mt-6 flex flex-col items-center gap-3">
            {shownRoutes.length < routes.length && <button className="btn btn-secondary" onClick={() => setVisibleCount((count) => Math.min(count + ROUTE_PAGE_SIZE, routes.length))}>Mostrar {Math.min(ROUTE_PAGE_SIZE, routes.length - shownRoutes.length)} opciones más</button>}
            <p className="text-sm text-muted" aria-live="polite">Ves {shownRoutes.length} de {routes.length} opciones. {comparison.length} de 2 seleccionadas para comparar.</p>
            {comparison.length > 0 && <a href="#comparacion-rutas" className="text-sm font-medium text-brand underline underline-offset-4">Ir a mi comparación</a>}
          </div>
        </section>
      )}

      {!loading && !tripData && !message && (
        <EmptyState icon={Map} title="¿A dónde vas?" text="Escribe un destino para consultar las opciones de transporte que conectan sus paraderos cercanos." />
      )}
    </div>
  );
}
