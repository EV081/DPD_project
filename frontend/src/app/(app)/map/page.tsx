'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { X, MapPinOff, RefreshCw } from 'lucide-react';
import { Spinner } from '@/components/Spinner';
import MapView from '@/components/MapView';
import { SYSTEMS } from '@/lib/systems';
import SearchAutocomplete from '@/components/SearchAutocomplete';
import TripSummaryCard from '@/components/TripSummaryCard';
import ForecastPanel from '@/components/ForecastPanel';
import SystemBadge from '@/components/SystemBadge';
import FeedbackBox from '@/components/FeedbackBox';
import BottomSheet from '@/components/BottomSheet';
import SosButton from '@/components/SosButton';
import ReportarModal from '@/components/ReportarModal';
import SeguridadAcceso from '@/components/SeguridadAcceso';
import RutaSegura, { CaminataMapa } from '@/components/RutaSegura';
import Alert from '@/components/Alert';
import HomeSheet from '@/components/HomeSheet';
import { useAuth } from '@/context/AuthContext';
import { getRecents, addRecent, RecentDestination } from '@/lib/recents';
import { getStations, getRouteGeoJson, getCaminata, getRouteCodeFromStation, matchTrip, getStationPrediction } from '@/lib/services';
import { opcionesDeViaje } from '@/lib/aforo';
import { tramoEntre } from '@/lib/route';
import { TRIP_STORAGE_KEY, FOCUS_STORAGE_KEY } from '@/lib/constants';
import { getUserLocation, LIMA_CENTER, Coords } from '@/lib/geolocation';
import { Station, TripMatchResponse, MatchedRoute, TramoTransbordo, AutocompleteSuggestion, ForecastView } from '@/lib/types';

// Trazado recortado entre un paradero de subida y uno de bajada (sin tocar el estado), o null si no hay trazado que cubra ambos
async function trazoDeTramo(subida: Station, bajada: Station): Promise<any | null> {
  const code = getRouteCodeFromStation(subida);
  const geo = await getRouteGeoJson(subida.system, code, true);
  let features: any[] = Array.isArray(geo) ? geo : geo?.features || [];
  if (code && features.length > 0) {
    const matched = features.filter((f) => {
      const p = f.properties || {};
      const v = p.ruta || p.servicio || p.osm_ref || p.codigo || p.estacion;
      return String(v).toLowerCase() === String(code).toLowerCase();
    });
    if (matched.length > 0) features = matched;
  }
  return tramoEntre(features, { lat: subida.latitude, lon: subida.longitude }, { lat: bajada.latitude, lon: bajada.longitude });
}

export default function MapPage() {
  const { user } = useAuth();
  const [recents, setRecents] = useState<RecentDestination[]>([]);
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
  const [showStations, setShowStations] = useState(false);   // apagado: el mapa solo muestra lo que se usa
  const [focus, setFocus] = useState<Coords | null>(null);
  const [forecastError, setForecastError] = useState(false);
  const [stationsError, setStationsError] = useState(false);
  const [walk, setWalk] = useState<CaminataMapa | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const lastLoad = useRef(0);                               // descarta respuestas de un paradero anterior
  const lastRequest = useRef<{ station: Station; haciaId?: string; tramo2?: TramoTransbordo } | null>(null);

  useEffect(() => { setRecents(getRecents()); }, []);

  // Ubicación + red de estaciones
  const loadNetwork = useCallback(async () => {
    setStationsError(false);
    const [loc, all] = await Promise.all([
      getUserLocation().catch(() => null),
      getStations().catch((e) => { console.error('Error cargando estaciones:', e); setStationsError(true); return [] as Station[]; }),
    ]);
    setLocationDenied(!loc);
    setLocation((prev) => (loc ? loc : prev ?? LIMA_CENTER));
    setStations(all);
    setLoadingMap(false);
  }, []);

  useEffect(() => { loadNetwork(); }, [loadNetwork]);

  const loadStation = useCallback(async (station: Station, openCard = true, haciaId?: string, tramo2?: TramoTransbordo) => {
    const mine = ++lastLoad.current;
    const vigente = () => mine === lastLoad.current;
    lastRequest.current = { station, haciaId, tramo2 };
    if (openCard) setSelectedStation(station);
    setLoadingForecast(true);
    setForecastError(false);
    setForecast(null);
    setRouteGeoJson(null);

    try {
      const routeCode = getRouteCodeFromStation(station);
      const geo = await getRouteGeoJson(station.system, routeCode, !!haciaId);
      if (!vigente()) return;
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
        // Si ningún trazado pasa cerca de ambos paraderos no se dibuja otra línea (una ruta equivocada confunde más que ninguna)
        features = tramo ? [tramo] : [];
      }
      // Viaje con transbordo: se dibuja también el segundo tramo
      if (tramo2) {
        const sube2 = stations.find((s) => s.id === tramo2.boarding_id);
        const baja2 = stations.find((s) => s.id === tramo2.leaving_id);
        if (sube2 && baja2) {
          const t2 = await trazoDeTramo(sube2, baja2);
          if (!vigente()) return;
          if (t2) {
            const baja1 = haciaId ? stations.find((s) => s.id === haciaId) : undefined;
            // Caminata entre paraderos por las calles; si el servicio falla, línea recta
            let aPie: any[] = [];
            if (baja1) {
              let coordenadas: number[][] = [[baja1.longitude, baja1.latitude], [sube2.longitude, sube2.latitude]];
              try {
                const calle = (await getCaminata(baja1, sube2))?.geojson?.geometry?.coordinates;
                if (Array.isArray(calle) && calle.length > 1) coordenadas = [[baja1.longitude, baja1.latitude], ...calle, [sube2.longitude, sube2.latitude]];
              } catch { /* sin servicio de rutas a pie: se deja la línea recta */ }
              if (!vigente()) return;
              aPie = [{ type: 'Feature', properties: { color_hex: '#64748b', punteada: true }, geometry: { type: 'LineString', coordinates: coordenadas } }];
            }
            features = [...features, ...aPie, t2];
          }
        }
      }
      if (features.length > 0) setRouteGeoJson({ type: 'FeatureCollection', features });
    } catch (error) {
      console.error('Error al obtener GeoJSON de la ruta:', error);
    }

    try {
      // Una sola llamada: estado actual + pronóstico del día (sentido según el destino, si hay)
      const data = await getStationPrediction(station, haciaId);
      if (!vigente()) return;
      setForecastStation(station);
      setForecastAt(Date.now());
      setForecast(data ? { current: data.current, predictions: data.forecast, referencia: data.referencia } : { sinDatos: true });
    } catch (error) {
      console.error('Error al obtener predicciones:', error);
      if (vigente()) setForecastError(true);
    } finally {
      if (vigente()) setLoadingForecast(false);
    }
  }, [stations]);

  const showRoute = useCallback((trip: TripMatchResponse, route: MatchedRoute) => {
    setTripData(trip);
    setSelectedRoute(route);
    setSelectedStation(null);
    setFilterIds([route.boarding_id, route.leaving_id, ...(route.transbordo ? [route.transbordo.boarding_id, route.transbordo.leaving_id] : [])]);
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
      if (boarding) loadStation(boarding, false, route.leaving_id, route.transbordo);
    } catch (e) {
      console.error(e);
    }
  }, [location, stations, showRoute, loadStation]);

  // Paradero elegido desde su detalle ("Ver en el mapa"): se muestra solo ese paradero y su ficha
  useEffect(() => {
    if (stations.length === 0) return;
    const id = sessionStorage.getItem(FOCUS_STORAGE_KEY);
    if (!id) return;
    sessionStorage.removeItem(FOCUS_STORAGE_KEY);
    const st = stations.find((s) => s.id === id);
    if (!st) return;
    setFilterIds([st.id]);
    setFocus({ lat: st.latitude, lon: st.longitude });
    loadStation(st);
  }, [stations, loadStation]);

  const handleSearchDestination = async (input: string | AutocompleteSuggestion) => {
    if (!location) return;
    setNotice(null);
    closeTrip();   // una búsqueda nueva no deja la ruta anterior dibujada (si no hay ruta, el mapa queda limpio)
    const dest = typeof input === 'string' ? input : { lat: input.lat, lon: input.lon };
    try {
      const respuesta = await matchTrip(location.lat, location.lon, dest);
      const response = typeof input === 'string' ? respuesta
        : { ...respuesta, destination: { ...respuesta.destination, resolved_name: input.display_name } };
      const { rutas: ofrecibles } = opcionesDeViaje(response);   // sin ruta directa llegan los transbordos; la tarjeta lo explica
      if (ofrecibles.length === 0) {
        setNotice('No se encontró una ruta a ese destino, ni directa ni con un transbordo, dentro del radio de búsqueda.');
        return;
      }
      const best = ofrecibles[0]; // la de menor costo generalizado
      setRecents(addRecent(
        typeof input === 'string'
          ? { label: input }
          : { label: input.display_name, lat: input.lat, lon: input.lon },
      ));
      showRoute(response, best);
      const boarding = stations.find((s) => s.id === best.boarding_id);
      if (boarding) loadStation(boarding, false, best.leaving_id, best.transbordo);
    } catch (error) {
      console.error('Error al planificar el viaje:', error);
      setNotice('No se pudo planificar el viaje. Inténtalo de nuevo.');
    }
  };

  const retryForecast = () => { if (lastRequest.current) loadStation(lastRequest.current.station, false, lastRequest.current.haciaId, lastRequest.current.tramo2); };

  const closeTrip = () => {
    lastLoad.current++;
    setWalk(null);
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
        showAll={showStations}
        focus={focus}
        routeGeoJson={routeGeoJson}
        walk={walk}
        destination={tripData ? { lat: tripData.destination.lat, lon: tripData.destination.lon, name: tripData.destination.resolved_name } : null}
        onStationClick={(s) => { if (!tripData) loadStation(s); }}
      />

      {/* Buscador: ancho completo en móvil, tarjeta lateral en pantallas grandes */}
      <div className="absolute left-3 right-3 top-3 z-[1000] md:right-auto md:left-4 md:top-4 md:w-[26rem]">
        <div className="flex items-start gap-2">
          <SearchAutocomplete className="min-w-0 flex-1" variant="float" onSelectDestination={handleSearchDestination} onSearchSubmit={handleSearchDestination} />
          <SosButton className="!h-[3.375rem] shrink-0" onReport={() => setReportOpen(true)} />
        </div>
        {locationDenied && (
          <p className="float-panel mt-2 flex items-start gap-2 px-3.5 py-2.5 text-sm text-muted">
            <MapPinOff size={16} className="mt-0.5 shrink-0 text-warn" />
            Sin acceso a tu ubicación: se usa el centro de Lima como punto de partida.
          </p>
        )}
        {stationsError && (
          <div className="float-panel mt-2 flex items-center gap-3 px-3.5 py-2.5 text-sm text-fg">
            <span className="min-w-0 flex-1">No se pudo cargar la red de paraderos.</span>
            <button onClick={loadNetwork} className="btn btn-secondary !px-3 !py-1.5 !text-[0.8125rem]"><RefreshCw size={14} /> Reintentar</button>
          </div>
        )}
        {notice && <p className="float-panel mt-2 px-3.5 py-2.5 text-sm text-fg">{notice}</p>}
      </div>

      {/* Leyenda de sistemas (solo pantallas grandes) */}
      <div className={`float-panel absolute bottom-7 right-4 z-[900] hidden px-3.5 py-3 ${showStations || filterIds ? 'md:block' : ''}`}>
        <ul className="space-y-1.5">
          {Object.values(SYSTEMS).map((s) => (
            <li key={s.id} className="flex items-center gap-2 text-xs text-muted">
              <span className="h-2.5 w-2.5 rounded-full ring-2 ring-surface" style={{ backgroundColor: s.color }} />
              {s.label}
            </li>
          ))}
        </ul>
      </div>

      {/* Panel: hoja inferior en móvil, tarjeta flotante a la izquierda en escritorio */}
      <div className="absolute inset-x-3 bottom-3 z-[1000] md:inset-x-auto md:bottom-4 md:left-4 md:w-[26rem]">
        {tripData && selectedRoute && (
          <TripSummaryCard
            tripData={tripData} selectedRoute={selectedRoute} forecast={forecast} loadingForecast={loadingForecast} forecastError={forecastError} onRetry={retryForecast} onClose={closeTrip}
            walkSlot={(() => {
              const boarding = stations.find((st) => st.id === selectedRoute.boarding_id);
              return boarding ? (
                <div className="space-y-4">
                  <RutaSegura station={boarding} origen={location} origenReal={!locationDenied} auto onChange={setWalk} />
                  <SeguridadAcceso station={boarding} />
                </div>
              ) : null;
            })()}
          >
            {feedbackBox}
          </TripSummaryCard>
        )}

        {!tripData && selectedStation && (
          <BottomSheet
            key={selectedStation.id}
            header={
              <header className="flex items-start justify-between gap-3 px-5 pb-3 pt-1">
                <div className="min-w-0">
                  <SystemBadge system={selectedStation.system} />
                  <h3 className="mt-2 truncate text-lg font-bold text-fg">{selectedStation.name}</h3>
                  <p className="truncate text-sm text-muted">{selectedStation.avenida || 'Sin referencia'}</p>
                </div>
                <button onClick={() => { lastLoad.current++; setSelectedStation(null); setRouteGeoJson(null); setFilterIds(null); setWalk(null); setForecast(null); }} aria-label="Cerrar" className="btn btn-ghost !rounded-full !bg-surface-2 !p-2">
                  <X size={18} />
                </button>
              </header>
            }
          >
            <div className="px-5 pb-5">
              <ForecastPanel forecast={forecast} loading={loadingForecast} error={forecastError} onRetry={retryForecast} />
              {feedbackBox}
              <div className="mt-5 space-y-4 border-t border-line pt-4">
                <SeguridadAcceso station={selectedStation} />
                <RutaSegura station={selectedStation} origen={location} origenReal={!locationDenied} onChange={setWalk} />
              </div>
            </div>
          </BottomSheet>
        )}

        {!tripData && !selectedStation && (
          <HomeSheet
            name={user?.name}
            recents={recents}
            showStations={showStations}
            onReport={() => setReportOpen(true)}
            onToggleStations={() => {
              setShowStations((v) => !v);
              if (filterIds) setFilterIds(null);   // salir del paradero enfocado
            }}
            onPickRecent={(r) =>
              handleSearchDestination(r.lat != null && r.lon != null ? { display_name: r.label, lat: r.lat, lon: r.lon } : r.label)
            }
          />
        )}
      </div>
      {reportOpen && <ReportarModal ubicacion={location} ubicacionReal={!locationDenied} onClose={() => setReportOpen(false)} />}
    </div>
  );
}
