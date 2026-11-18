'use client';

import { Modal as MantineModal } from '@mantine/core';

interface Props {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
  size?: 'md' | 'lg' | 'xl';
}

export default function Modal({ title, onClose, children, className = '', size = 'md' }: Props) {
  return <MantineModal opened onClose={onClose} title={title} centered size={size} zIndex={2200}
    className={className} overlayProps={{ backgroundOpacity: 0.5, blur: 3 }}
    closeButtonProps={{ 'aria-label': 'Cerrar' }}
    classNames={{ content: 'us-modal', header: 'us-modal-header', title: 'us-modal-title' }}>
    {children}
  </MantineModal>;
}
