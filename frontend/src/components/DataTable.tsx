'use client';

import { useId, useMemo, useState } from 'react';
import { ActionIcon, Button, Group, Select, TextInput } from '@mantine/core';
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Download, Search } from 'lucide-react';
import { flexRender, getCoreRowModel, getFilteredRowModel, getPaginationRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState } from '@tanstack/react-table';
import { downloadCsv } from '@/lib/csv';

export interface DataColumn<T> { id: string; label: string; value: (row: T) => string | number | null; render?: (row: T) => React.ReactNode }
export default function DataTable<T>({ rows, columns, title, searchable = true }: {
  rows: T[]; columns: DataColumn<T>[]; title: string; searchable?: boolean;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [query, setQuery] = useState('');
  const id = useId();
  const definitions = useMemo<ColumnDef<T>[]>(() => columns.map((c) => ({
    id: c.id, header: c.label, accessorFn: c.value,
    cell: (ctx) => c.render ? c.render(ctx.row.original) : String(ctx.getValue() ?? '—'),
  })), [columns]);
  const table = useReactTable({ data: rows, columns: definitions,
    state: { sorting, globalFilter: query }, onSortingChange: setSorting, onGlobalFilterChange: setQuery,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(), getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } }, globalFilterFn: 'includesString',
  });
  const filtered = table.getFilteredRowModel().rows.length;
  return <div className="us-data-table">
    <Group justify="space-between" gap="xs" mb="sm" wrap="wrap">
      {searchable && <TextInput size="xs" aria-label={`Buscar en ${title}`} placeholder="Buscar en la tabla…"
        value={query} onChange={(e) => setQuery(e.currentTarget.value)} leftSection={<Search size={14} />} />}
      <Button size="compact-xs" variant="subtle" leftSection={<Download size={14} />} disabled={!filtered}
        onClick={() => downloadCsv(title, columns.map((c) => c.label), table.getSortedRowModel().rows.map((r) => columns.map((c) => c.value(r.original))))}>CSV</Button>
    </Group>
    <div className="us-table-scroll" tabIndex={0} role="region" aria-label={title}>
      <table>
        <caption className="sr-only">{title}</caption>
        <thead>{table.getHeaderGroups().map((g) => <tr key={g.id}>{g.headers.map((h) => <th key={h.id} scope="col" aria-sort={h.column.getIsSorted() === 'asc' ? 'ascending' : h.column.getIsSorted() === 'desc' ? 'descending' : 'none'}>
          <button type="button" onClick={h.column.getToggleSortingHandler()}>
            {flexRender(h.column.columnDef.header, h.getContext())}
            {h.column.getIsSorted() === 'asc' ? <ArrowUp size={13} /> : h.column.getIsSorted() === 'desc' ? <ArrowDown size={13} /> : <ArrowUpDown size={13} />}
          </button>
        </th>)}</tr>)}</thead>
        <tbody>{table.getRowModel().rows.map((r) => <tr key={r.id}>{r.getVisibleCells().map((c) => <td key={c.id}>{flexRender(c.column.columnDef.cell, c.getContext())}</td>)}</tr>)}
          {!filtered && <tr><td colSpan={columns.length} className="us-table-empty">No hay resultados. Prueba otra búsqueda.</td></tr>}
        </tbody>
      </table>
    </div>
    <div className="us-table-footer">
      <span role="status">{filtered} resultado{filtered === 1 ? '' : 's'} · Página {filtered ? table.getState().pagination.pageIndex + 1 : 0} de {table.getPageCount()}</span>
      <Group gap="xs">
        <label htmlFor={id} className="sr-only">Filas por página</label>
        <Select id={id} size="xs" w={72} allowDeselect={false} value={String(table.getState().pagination.pageSize)} data={['10', '25', '50']}
          onChange={(v) => table.setPageSize(Number(v ?? 10))} comboboxProps={{ withinPortal: false }} />
        <ActionIcon variant="default" aria-label="Página anterior" disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()}><ChevronLeft size={16} /></ActionIcon>
        <ActionIcon variant="default" aria-label="Página siguiente" disabled={!table.getCanNextPage()} onClick={() => table.nextPage()}><ChevronRight size={16} /></ActionIcon>
      </Group>
    </div>
  </div>;
}
