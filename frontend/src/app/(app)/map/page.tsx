'use client';

import { useCallback, useEffect, useState } from 'react';
import { X, MapPinOff } from 'lucide-react';
import { Spinner } from '@/components/Spinner';
import MapView from '@/components/MapView';
import { SYSTEMS } from '@/lib/systems';
import SearchAutocomplete from '@/components/SearchAutocomplete';
import TripSummaryCard from '@/components/TripSummaryCard';
import ForecastPanel from '@/components/ForecastPanel';
import SystemBadge from '@/components/SystemBadge';
import FeedbackBox from '@/components/FeedbackBox';
import { getStations, getRouteGeoJson, getRouteCodeFromStation, matchTrip, getStationPrediction } from '@/lib/services';
import { rutasOfrecibles } from '@/lib/aforo';
import { tramoEntre } from '@/lib/route';
import { TRIP_STORAGE_KEY } from '@/lib/constants';
import { getUserLocation, LIMA_CENTER, Coords } from '@/lib/geolocation';
import { Station, TripMatchResponse, MatchedRoute, AutocompleteSuggestion, ForecastView } from '@/lib/types';

export default function MapPage() {
  const [location, setLocation] = useState<Coords | null>(null);
  const [locationDenied, setLocationDenied] = useState(false);
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [forecast, setForecast] = useState<ForecastView | null>(null);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [forecastAt, setForecastAt] = useState(0);          // cuándo se mostró el ETA (para medir la espera real)
  const [forecastStation, setForecastStation] = useState<Station | null>(null);
  const [loadingMap, setLoadingMap] = useState(true);
  const [routeGeoJson, setRouteGeoJson] = useState<any | null>(null);
  const [tripData, setTripData] = useState<TripMatchResponse | null>(null);
  const [selectedRoute, setSelectedRoute] = useState<MatchedRoute | null>(null);
  const [filterIds, setFilterIds] = useState<string[] | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Ubicación + red de estaciones
  useEffect(() => {
    (async () => {
      const [loc, all] = await Promise.all([
        getUserLocation().catch(() => null),
        getStations().catch((e) => { console.error('Error cargando estaciones:', e); return [] as Station[]; }),
      ]);
      if (!loc) setLocationDenied(true);
      setLocation(loc ?? LIMA_CENTER);
      setStations(all);
      setLoadingMap(false);
    })();
  }, []);

  const loadStation = useCallback(async (station: Station, openCard = true, haciaId?: string) => {
    if (openCard) setSelectedStation(station);
    setLoadingForecast(true);
    setForecast(null);
    setRouteGeoJson(null);

    try {
      const routeCode = getRouteCodeFromStation(station);
      const geo = await getRouteGeoJson(station.system, routeCode);
      let features: any[] = Array.isArray(geo) ? geo : geo?.features || [];
      if (routeCode && features.length > 0) {
        const matched = features.filter((f) => {
          const p = f.properties || {};
          const v = p.ruta || p.servicio || p.osm_ref || p.codigo || p.estacion;
          return String(v).toLowerCase() === String(routeCode).toLowerCase();
        });
        if (matched.length > 0) features = matched;
      }
      // En un viaje solo importa el tramo subida → bajada, no todo el recorrido del servicio
      const bajada = haciaId ? stations.find((s) => s.id === haciaId) : undefined;
      if (bajada) {
        const tramo = tramoEntre(
          features,
          { lat: station.latitude, lon: station.longitude },
          { lat: bajada.latitude, lon: bajada.longitude },
        );
        if (tramo) features = [tramo];
      }
      if (features.length > 0) setRouteGeoJson({ type: 'FeatureCollection', features });
    } catch (error) {
      console.error('Error al obtener GeoJSON de la ruta:', error);
    }

    try {
      // Una sola llamada: estado actual + pronóstico del día (sentido según el destino, si hay)
      const data = await getStationPrediction(station, haciaId);
      setForecastStation(station);
      setForecastAt(Date.now());
      setForecast(data ? { current: data.current, predictions: data.forecast, referencia: data.referencia } : { sinDatos: true });
    } catch (error) {
      console.error('Error al obtener predicciones:', error);
    } finally {
      setLoadingForecast(false);
    }
  }, [stations]);

  const showRoute = useCallback((trip: TripMatchResponse, route: MatchedRoute) => {
    setTripData(trip);
    setSelectedRoute(route);
    setSelectedStation(null);
    setFilterIds([route.boarding_id, route.leaving_id]);
  }, []);

  // Ruta elegida en /destinations: llega por sessionStorage y se consume una vez
  useEffect(() => {
    if (!location || stations.length === 0) return;
    const raw = sessionStorage.getItem(TRIP_STORAGE_KEY);
    if (!raw) return;
    sessionStorage.removeItem(TRIP_STORAGE_KEY);
    try {
      const { selectedRoute: route, destination } = JSON.parse(raw);
      showRoute({ origin: location, destination, radius_meters: 1000, found_routes: [route] }, route);
      const boarding = stations.find((s) => s.id === route.boarding_id);
      if (boarding) loadStation(boarding, false, route.leaving_id);
    } catch (e) {
      console.error(e);
    }
  }, [location, stations, showRoute, loadStation]);

  const handleSearchDestination = async (input: string | AutocompleteSuggestion) => {
    if (!location) return;
    setNotice(null);
    const dest = typeof input === 'string' ? input : { lat: input.lat, lon: input.lon };
    try {
      const response = await matchTrip(location.lat, location.lon, dest);
      const ofrecibles = rutasOfrecibles(response.found_routes);
      if (ofrecibles.length === 0) {
        setNotice('No se encontró una ruta directa a ese destino dentro del radio de búsqueda.');
        return;
      }
      const best = ofrecibles[0]; // la de menor costo generalizado
      showRoute(response, best);
      const boarding = stations.find((s) => s.id === best.boarding_id);
      if (boarding) loadStation(boarding, false, best.leaving_id);
    } catch (error) {
      console.error('Error al planificar el viaje:', error);
      setNotice('No se pudo planificar el viaje. Inténtalo de nuevo.');
    }
  };

  const closeTrip = () => {
    setTripData(null);
    setSelectedRoute(null);
    setFilterIds(null);
    setRouteGeoJson(null);
    setForecast(null);
  };

  if (loadingMap || !location) {
    return (
      <div className="flex h-full min-h-[60dvh] flex-col items-center justify-center gap-3">
        <Spinner size={30} />
        <p className="text-sm text-muted">Obteniendo tu ubicación y la red de transporte…</p>
      </div>
    );
  }

  const feedbackBox =
    !loadingForecast && forecastStation && forecast && !forecast.sinDatos ? (
      <FeedbackBox station={forecastStation} current={forecast.current} consultedAt={forecastAt} />
    ) : null;

  return (
    <div className="relative h-full w-full">
      <MapView
        center={location}
        stations={stations}
        filterIds={filterIds}
        routeGeoJson={routeGeoJson}
        destination={tripData ? { lat: tripData.destination.lat, lon: tripData.destination.lon, name: tripData.destination.resolved_name } : null}
        onStationClick={(s) => { if (!tripData) loadStation(s); }}
      />

      {/* Buscador: ancho completo en móvil, tarjeta lateral en pantallas grandes */}
      <div className="absolute left-3 right-3 top-3 z-[1000] md:right-auto md:left-4 md:top-4 md:w-[26rem]">
        <SearchAutocomplete variant="float" onSelectDestination={handleSearchDestination} onSearchSubmit={handleSearchDestination} />
        {locationDenied && (
          <p className="float-panel mt-2 flex items-start gap-2 px-3.5 py-2.5 text-sm text-muted">
            <MapPinOff size={16} className="mt-0.5 shrink-0 text-amber-600" />
            Sin acceso a tu ubicación: se usa el centro de Lima como punto de partida.
          </p>
        )}
        {notice && <p className="float-panel mt-2 px-3.5 py-2.5 text-sm text-fg">{notice}</p>}
      </div>

      {/* Leyenda de sistemas (solo pantallas grandes) */}
      <div className="float-panel absolute bottom-7 right-4 z-[900] hidden px-3.5 py-3 md:block">
        <ul className="space-y-1.5">
          {Object.values(SYSTEMS).map((s) => (
            <li key={s.id} className="flex items-center gap-2 text-xs text-muted">
              <span className="h-2.5 w-2.5 rounded-full ring-2 ring-white dark:ring-[#111a2c]" style={{ backgroundColor: s.color }} />
              {s.label}
            </li>
          ))}
        </ul>
      </div>

      {/* Panel: hoja inferior en móvil, tarjeta flotante a la izquierda en escritorio */}
      <div className="absolute inset-x-3 bottom-3 z-[1000] md:inset-x-auto md:bottom-4 md:left-4 md:w-[26rem]">
        {tripData && selectedRoute && (
          <TripSummaryCard tripData={tripData} selectedRoute={selectedRoute} forecast={forecast} loadingForecast={loadingForecast} onClose={closeTrip}>
            {feedbackBox}
          </TripSummaryCard>
        )}

        {!tripData && selectedStation && (
          <div className="float-panel max-h-[55dvh] overflow-y-auto md:max-h-[calc(100dvh-8rem)]">
            <header className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-line bg-surface px-5 py-4">
              <div className="min-w-0">
                <SystemBadge system={selectedStation.system} />
                <h3 className="mt-2 truncate text-lg font-semibold text-fg">{selectedStation.name}</h3>
                <p className="truncate text-sm text-muted">{selectedStation.avenida || 'Sin referencia'}</p>
              </div>
              <button onClick={() => { setSelectedStation(null); setRouteGeoJson(null); }} aria-label="Cerrar" className="btn btn-ghost !p-1.5">
                <X size={18} />
              </button>
            </header>
            <div className="p-5">
              <ForecastPanel forecast={forecast} loading={loadingForecast} />
              {feedbackBox}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
