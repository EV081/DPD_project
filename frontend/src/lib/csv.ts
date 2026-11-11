/** Escape CSV y evita que las cadenas se interpreten como fórmulas al abrir una hoja. */
export function encodeCsv(headers: string[], rows: (string | number | null)[][]) {
  return '\uFEFF' + [headers, ...rows].map((row) => row.map((value) => {
    const text = String(value ?? '');
    const safe = typeof value === 'string' && /^\s*[=+\-@]/.test(text) ? "'" + text : text;
    return '"' + safe.replaceAll('"', '""') + '"';
  }).join(',')).join('\r\n');
}
export function downloadCsv(title: string, headers: string[], rows: (string | number | null)[][]) {
  const url = URL.createObjectURL(new Blob([encodeCsv(headers, rows)], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `UrbanSafe_${title.replace(/[^\p{L}\p{N}]+/gu, '_')}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
