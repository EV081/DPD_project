'use client';

import { Alert as MantineAlert } from '@mantine/core';
import { CheckCircle2, Info, TriangleAlert, OctagonAlert } from 'lucide-react';

type Tono = 'info' | 'ok' | 'warn' | 'danger';
const TONOS = {
  info: { color: 'blue', icon: Info }, ok: { color: 'green', icon: CheckCircle2 },
  warn: { color: 'yellow', icon: TriangleAlert }, danger: { color: 'red', icon: OctagonAlert },
};
export default function Alert({ tono = 'info', children, className = '' }: { tono?: Tono; children: React.ReactNode; className?: string }) {
  const { color, icon: Icon } = TONOS[tono];
  return <MantineAlert color={color} variant="light" radius="md" icon={<Icon size={18} />}
    role={tono === 'danger' ? 'alert' : 'status'} className={className}>{children}</MantineAlert>;
}
