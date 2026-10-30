// Marca de UrbanSafe: escudo (seguridad) con una ruta que lo atraviesa
export function LogoMark({ size = 32, className = '' }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#2563eb" />
      <path d="M16 5.5 24 8.6v6.2c0 4.7-3.2 8.2-8 10.2-4.8-2-8-5.5-8-10.2V8.6L16 5.5Z" fill="white" fillOpacity=".16" stroke="white" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M11.5 20c2.2-.2 2.4-3.4 4.5-3.6 2.4-.2 2.1-3.2 4.5-3.4" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="11.5" cy="20" r="1.6" fill="white" />
      <circle cx="20.5" cy="13" r="1.6" fill="white" />
    </svg>
  );
}

export function Logo({ size = 32, showText = true }: { size?: number; showText?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark size={size} />
      {showText && <span className="text-lg font-bold tracking-tight text-fg">UrbanSafe</span>}
    </span>
  );
}
