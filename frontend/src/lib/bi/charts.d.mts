import type { VistaBi } from './data.mjs';
export function escapeHTML(value: unknown): string;
export function formatValue(value: number | null | undefined, unit?: string): string;
export function renderChart(view: VistaBi): string;
export function tableForView(view: VistaBi): { headers: string[]; rows: (string | number)[][] };
