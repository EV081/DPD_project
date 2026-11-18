import creditos from '../../public/imagenes/fotografias-reales-creditos.json';

type Credito = { file: string; author: string; license: string };

const LICENCIAS: Record<string, string> = { 'Unsplash License': 'Unsplash', 'Pexels License': 'Pexels' };

/** Pie de foto con autor y licencia, tomado del registro de créditos. null si la imagen no está registrada. */
export function creditoFoto(archivo: string): string | null {
  const item = (creditos as Credito[]).find((c) => c.file === archivo);
  if (!item) return null;
  const autor = item.author.replace(/\s*\(.*\)\s*$/, '');
  return `Foto: ${autor} · ${LICENCIAS[item.license] ?? item.license}`;
}
