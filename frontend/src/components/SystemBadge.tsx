import { systemInfo } from '@/lib/systems';

export default function SystemBadge({ system }: { system: string }) {
  const info = systemInfo(system);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${info.badge}`}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: info.color }} />
      {info.label}
    </span>
  );
}
