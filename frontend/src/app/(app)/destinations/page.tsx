'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, Map, Bus, ChevronRight, TriangleAlert, Footprints, Lightbulb, Clock } from 'lucide-react';
import SearchAutocomplete from '@/components/SearchAutocomplete';
import SystemBadge from '@/components/SystemBadge';
import { Spinner, EmptyState } from '@/components/Spinner';
import { matchTrip } from '@/lib/services';
import { rutasOfrecibles, etiquetaClase, claseAforo, textoOcupacion } from '@/lib/aforo';
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
      const response = await matchTrip(origin.lat, origin.lon, dest);
      setTripData(response);
      if (rutasOfrecibles(response.found_routes).length === 0) {
        setMessage('No se encontraron rutas directas a este destino dentro del radio de búsqueda.');
      }
    } catch (error) {
      console.error('Error al planificar el viaje:', error);
      setMessage('Ocurrió un error al buscar rutas hacia tu destino. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const routes = tripData ? rutasOfrecibles(tripData.found_routes) : [];

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-10">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-fg">Planificar viaje</h1>
        <p className="mt-1 text-sm text-muted">Indica tu destino y compara las rutas directas con su aforo y tiempo de espera.</p>
      </header>

      <SearchAutocomplete className="relative z-20 mt-6" placeholder="¿A qué lugar o avenida te diriges?"
        onSelectDestination={search} onSearchSubmit={search} />
      {locationNote && <p className="mt-2 text-xs text-muted">{locationNote}</p>}

      {loading && (
        <div className="flex items-center justify-center gap-2.5 py-20 text-sm text-muted"><Spinner size={18} /> Buscando las mejores rutas…</div>
      )}

      {!loading && message && (
        <p role="status" className="mt-8 flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          <TriangleAlert size={18} className="mt-0.5 shrink-0" /> {message}
        </p>
      )}

      {!loading && tripData && routes.length > 0 && (
        <section className="mt-8" aria-label="Resultados">
          <div className="card flex items-center gap-3 p-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-rose-500/12 text-rose-600 dark:text-rose-300">
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

          {tripData.recomendacion_viaje?.mensaje && (
            <p className="mt-3 flex gap-2.5 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-300">
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
                  className={`card group relative p-5 text-left transition-colors hover:border-brand/60 ${best ? '!border-brand ring-1 ring-brand/30' : ''}`}
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
                      <p className="mt-2.5 text-base font-semibold text-fg">Sube en {item.boarding_station}</p>
                    </div>
                    <ChevronRight size={18} className="mt-1 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand" />
                  </div>

                  <ul className="mt-4 space-y-2 text-sm text-muted">
                    <li className="flex items-center gap-2.5"><Footprints size={16} className="shrink-0" /> {walkTo} m caminando hasta el paradero</li>
                    <li className="flex items-center gap-2.5"><Bus size={16} className="shrink-0" /> Bájate en <b className="font-semibold text-fg">{item.leaving_station}</b> · {walkFrom} m al destino</li>
                  </ul>

                  {item.aforo?.clase && (
                    <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line pt-3 text-sm">
                      <span className={`font-semibold ${claseAforo(item.aforo.clase)}`}>
                        {etiquetaClase(item.aforo.clase)} · {textoOcupacion(item.aforo.ocupacion)}
                      </span>
                      {item.espera_min != null && (
                        <span className="flex items-center gap-1.5 text-muted"><Clock size={14} /> Espera ~{item.espera_min} min</span>
                      )}
                      {item.viaje_min != null && <span className="text-muted">Viaje ~{Math.round(item.viaje_min)} min</span>}
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
