'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, Map, Bus, ChevronRight, TriangleAlert, Footprints, Lightbulb, Clock, Repeat2 } from 'lucide-react';
import SearchAutocomplete from '@/components/SearchAutocomplete';
import SystemBadge from '@/components/SystemBadge';
import { Skeleton, EmptyState } from '@/components/Spinner';
import { matchTrip } from '@/lib/services';
import { opcionesDeViaje, etiquetaClase, claseAforo, textoOcupacion } from '@/lib/aforo';
import { getUserLocation, LIMA_CENTER, Coords } from '@/lib/geolocation';
import { TRIP_STORAGE_KEY } from '@/lib/constants';
import { TripMatchResponse, AutocompleteSuggestion } from '@/lib/types';

export default function DestinationsPage() {
  const router = useRouter();
  const [location, setLocation] = useState<Coords | null>(null);
  const [tripData, setTripData] = useState<TripMatchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [locationNote, setLocationNote] = useState<string | null>(null);

  useEffect(() => {
    getUserLocation()
      .then(setLocation)
      .catch(() => {
        setLocation(LIMA_CENTER);
        setLocationNote('Sin acceso a tu ubicación: se usa el centro de Lima como punto de partida.');
      });
  }, []);

  const search = async (input: string | AutocompleteSuggestion) => {
    const origin = location ?? LIMA_CENTER;
    setLoading(true);
    setMessage(null);
    setTripData(null);
    try {
      const dest = typeof input === 'string' ? input : { lat: input.lat, lon: input.lon };
      const respuesta = await matchTrip(origin.lat, origin.lon, dest);
      // Con coordenadas el backend no sabe cómo se llama el lugar: se usa el nombre que eligió la persona
      const response = typeof input === 'string' ? respuesta
        : { ...respuesta, destination: { ...respuesta.destination, resolved_name: input.display_name } };
      setTripData(response);
      if (opcionesDeViaje(response).rutas.length === 0) {
        setMessage('No se encontraron rutas a este destino, ni directas ni con un transbordo, dentro del radio de búsqueda.');
      }
    } catch (error) {
      console.error('Error al planificar el viaje:', error);
      setMessage('Ocurrió un error al buscar rutas hacia tu destino. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const { rutas: routes, conTransbordo } = tripData ? opcionesDeViaje(tripData) : { rutas: [], conTransbordo: false };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-10">
      <header className="hero p-6 md:p-8">
        <div className="pointer-events-none absolute -right-10 -top-16 h-56 w-56 rounded-full bg-sky-400/30 blur-3xl" />
        <h1 className="relative text-3xl font-bold tracking-tight">¿A dónde vas hoy?</h1>
        <p className="relative mt-1.5 max-w-xl text-sm text-blue-100/90">Compara rutas directas con su aforo y tiempo de espera, y elige la que mejor te conviene.</p>
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
          <div className="card flex items-center gap-3 p-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-danger/12 text-danger">
              <MapPin size={19} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="eyebrow">Destino</p>
              <p className="truncate font-semibold text-fg">{tripData.destination.resolved_name}</p>
            </div>
            <span className="shrink-0 rounded-full bg-brand-soft px-3 py-1 text-sm font-semibold text-brand">
              {routes.length} {routes.length === 1 ? 'opción' : 'opciones'}
            </span>
          </div>

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

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {routes.map((item, index) => {
              const walkTo = Math.round(item.origin_walk_m);
              const walkFrom = Math.round(item.dest_walk_m);
              const best = index === 0;
              return (
                <button
                  key={`${item.boarding_id}-${item.route_code}-${index}`}
                  onClick={() => {
                    sessionStorage.setItem(TRIP_STORAGE_KEY, JSON.stringify({ selectedRoute: item, destination: tripData.destination }));
                    router.push('/map');
                  }}
                  className={`card group relative p-5 text-left ${best ? '!border-brand ring-1 ring-brand/30' : ''}`}
                >
                  {best && (
                    <span className="absolute -top-2.5 left-4 rounded-full bg-brand px-2.5 py-0.5 text-xs font-semibold text-white dark:text-[#06101f]">
                      Recomendada
                    </span>
                  )}
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <SystemBadge system={item.system} />
                        {item.route_code && <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs font-semibold text-fg">Ruta {item.route_code}</span>}
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

                  {item.transbordo && item.costo_generalizado_min != null && (
                    <div className="mt-4 grid grid-cols-3 gap-2 border-t border-line pt-4 text-center">
                      <div className="rounded-xl bg-surface-2 px-2 py-2.5">
                        <p className="text-sm font-bold tabular-nums text-fg">≈ {Math.round(item.costo_generalizado_min)} min</p>
                        <p className="text-xs text-muted">En total</p>
                      </div>
                      <div className="rounded-xl bg-surface-2 px-2 py-2.5">
                        <p className="text-sm font-bold tabular-nums text-fg">{item.viaje_min != null ? `${Math.round(item.viaje_min)} min` : '—'}</p>
                        <p className="text-xs text-muted">A bordo</p>
                      </div>
                      <div className="rounded-xl bg-surface-2 px-2 py-2.5">
                        <p className="text-sm font-bold tabular-nums text-fg">{item.caminata_min != null ? `${Math.round(item.caminata_min)} min` : '—'}</p>
                        <p className="text-xs text-muted">Caminando</p>
                      </div>
                    </div>
                  )}

                  {item.aforo?.clase && (
                    <div className="mt-4 grid grid-cols-3 gap-2 border-t border-line pt-4 text-center">
                      <div className="rounded-xl bg-surface-2 px-2 py-2.5">
                        <p className={`text-sm font-bold ${claseAforo(item.aforo.clase)}`}>{etiquetaClase(item.aforo.clase)}</p>
                        <p className="text-xs text-muted">{textoOcupacion(item.aforo.ocupacion)} ocupado</p>
                      </div>
                      <div className="rounded-xl bg-surface-2 px-2 py-2.5">
                        <p className="flex items-center justify-center gap-1 text-sm font-bold tabular-nums text-fg"><Clock size={13} />{item.espera_min != null ? `${item.espera_min} min` : '—'}</p>
                        <p className="text-xs text-muted">Espera</p>
                      </div>
                      <div className="rounded-xl bg-surface-2 px-2 py-2.5">
                        <p className="text-sm font-bold tabular-nums text-fg">{item.viaje_min != null ? `${Math.round(item.viaje_min)} min` : '—'}</p>
                        <p className="text-xs text-muted">Viaje</p>
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </section>
      )}

      {!loading && !tripData && !message && (
        <EmptyState icon={Map} title="¿A dónde vas?" text="Escribe un destino y te mostraremos los paraderos cercanos con sus rutas directas." />
      )}
    </div>
  );
}
