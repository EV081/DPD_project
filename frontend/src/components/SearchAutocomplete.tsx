'use client';

import { useEffect, useId, useState } from 'react';
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

export default function SearchAutocomplete({
  onSelectDestination, onSearchSubmit, placeholder = '¿A dónde quieres ir?', className = '', variant = 'inline',
}: Props) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const listId = useId();

  // Sugerencias con debounce mientras se escribe
  useEffect(() => {
    if (query.trim().length < 3) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        setSuggestions(await getAutocompleteSuggestions(query));
        setOpen(true);
      } catch (error) {
        console.error('Error en autocompletado:', error);
      } finally {
        setLoading(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [query]);

  const select = (item: AutocompleteSuggestion) => {
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
          setOpen(false);
          if (query.trim()) onSearchSubmit(query);
        }}
        className={`flex items-center gap-2.5 rounded-xl border border-line bg-surface px-3.5 py-2.5 transition-shadow focus-within:border-brand focus-within:ring-[3px] focus-within:ring-[var(--ring)] ${
          variant === 'float' ? 'shadow-[var(--shadow-float)]' : 'shadow-[var(--shadow-card)]'
        }`}
      >
        <Search size={18} className="shrink-0 text-muted" />
        <input
          className="min-w-0 flex-1 bg-transparent text-[0.9375rem] text-fg outline-none placeholder:text-muted"
          placeholder={placeholder}
          aria-label={placeholder}
          aria-controls={listId}
          aria-expanded={open}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {loading && <Spinner size={16} />}
        {query.length > 0 && !loading && (
          <button type="button" onClick={() => { setQuery(''); setSuggestions([]); }} aria-label="Limpiar búsqueda"
            className="rounded-md p-1 text-muted hover:bg-surface-2 hover:text-fg">
            <X size={16} />
          </button>
        )}
      </form>

      {open && suggestions.length > 0 && (
        <ul id={listId} role="listbox"
          className="float-panel absolute left-0 right-0 z-[1100] mt-2 max-h-72 overflow-y-auto py-1">
          {suggestions.map((item, i) => (
            <li key={i} role="option" aria-selected={false}>
              <button type="button" onClick={() => select(item)}
                className="flex w-full items-start gap-3 px-3.5 py-2.5 text-left hover:bg-surface-2">
                <MapPin size={16} className="mt-0.5 shrink-0 text-muted" />
                <span className="line-clamp-2 text-sm text-fg">{item.display_name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
