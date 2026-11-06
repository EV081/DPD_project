'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { Search, X, MapPin } from 'lucide-react';
import { getAutocompleteSuggestions } from '@/lib/services';
import { AutocompleteSuggestion } from '@/lib/types';
import { Spinner } from './Spinner';

interface Props {
  onSelectDestination: (suggestion: AutocompleteSuggestion) => void;
  onSearchSubmit: (searchText: string) => void;
  placeholder?: string;
  className?: string;
  /** "float": sobre el mapa (con sombra elevada). "inline": dentro de una página. */
  variant?: 'float' | 'inline';
}

// "Miraflores, Provincia de Lima, Área Metropolitana de Lima, Lima, 15074, Perú" -> título y detalle cortos
const RUIDO = /^(province of lima|provincia de lima|lima metropolitana|lima metropolitan area|[áa]rea metropolitana de lima|per[uú]|peru|\d{5})$/i;
const partir = (nombre: string) => {
  const [titulo, ...resto] = nombre.split(',').map((p) => p.trim()).filter(Boolean);
  const detalle = resto.filter((p) => !RUIDO.test(p));
  return { titulo: titulo ?? nombre, detalle: detalle.slice(0, 3).join(', ') };
};

export default function SearchAutocomplete({
  onSelectDestination, onSearchSubmit, placeholder = '¿A dónde quieres ir?', className = '', variant = 'inline',
}: Props) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  // Texto puesto al elegir una sugerencia o al enviar: no debe disparar otra búsqueda de sugerencias
  const settled = useRef<string | null>(null);

  // Sugerencias con debounce mientras se escribe
  useEffect(() => {
    if (query === settled.current || query.trim().length < 3) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const results = await getAutocompleteSuggestions(query);
        if (cancelled) return;   // el texto cambió o se eligió algo mientras se esperaba la respuesta
        setSuggestions(results);
        setActive(-1);
        setOpen(true);
      } catch (error) {
        console.error('Error en autocompletado:', error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 400);
    return () => { cancelled = true; clearTimeout(timer); setLoading(false); };
  }, [query]);

  const select = (item: AutocompleteSuggestion) => {
    settled.current = item.display_name;
    setQuery(item.display_name);
    setOpen(false);
    onSelectDestination(item);
  };

  return (
    <div className={`relative ${className}`}>
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          settled.current = query;
          setOpen(false);
          setSuggestions([]);
          if (query.trim()) onSearchSubmit(query);
        }}
        className={`flex items-center gap-3 rounded-2xl border border-line bg-surface px-4 py-3.5 transition-shadow focus-within:border-brand focus-within:ring-[3px] focus-within:ring-[var(--ring)] ${
          variant === 'float' ? 'shadow-[var(--shadow-float)]' : 'shadow-[var(--shadow-card)]'
        }`}
      >
        <Search size={18} className="shrink-0 text-muted" />
        <input
          className="min-w-0 flex-1 bg-transparent text-[0.9375rem] text-fg outline-none placeholder:text-muted"
          placeholder={placeholder}
          aria-label={placeholder}
          role="combobox"
          aria-autocomplete="list"
          aria-controls={listId}
          aria-expanded={open}
          aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
          name="destino"
          type="search"
          enterKeyHint="search"
          spellCheck={false}
          autoComplete="off"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (!open || suggestions.length === 0) return;
            if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => (i + 1) % suggestions.length); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => (i <= 0 ? suggestions.length - 1 : i - 1)); }
            else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); select(suggestions[active]); }
            else if (e.key === 'Escape') setOpen(false);
          }}
        />
        {loading && <Spinner size={16} />}
        <span className="sr-only" aria-live="polite">{open ? `${suggestions.length} sugerencias` : ''}</span>
        {query.length > 0 && !loading && (
          <button type="button" onClick={() => { setQuery(''); setSuggestions([]); }} aria-label="Limpiar búsqueda"
            className="-mr-1.5 rounded-lg p-2 text-muted hover:bg-surface-2 hover:text-fg">
            <X size={16} />
          </button>
        )}
      </form>

      {open && suggestions.length > 0 && (
        <ul id={listId} role="listbox"
          className="float-panel absolute left-0 right-0 z-[1100] mt-2 max-h-72 overflow-y-auto py-1">
          {suggestions.map((item, i) => (
            <li key={i} id={`${listId}-${i}`} role="option" aria-selected={i === active}>
              <button type="button" tabIndex={-1} onClick={() => select(item)}
                className={`flex w-full items-start gap-3 px-3.5 py-2.5 text-left hover:bg-surface-2 ${i === active ? 'bg-surface-2' : ''}`}>
                <MapPin size={16} className="mt-0.5 shrink-0 text-muted" />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-fg">{partir(item.display_name).titulo}</span>
                  {partir(item.display_name).detalle && <span className="block truncate text-xs text-muted">{partir(item.display_name).detalle}</span>}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
