export interface Coords { lat: number; lon: number }

// Centro de Lima: se usa si el usuario niega la ubicación o el navegador no la ofrece
export const LIMA_CENTER: Coords = { lat: -12.0464, lon: -77.0428 };

export const getUserLocation = (): Promise<Coords> =>
  new Promise((resolve, reject) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      reject(new Error('Geolocalización no disponible'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      reject,
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });
