'use client';

import { forwardRef, useId } from 'react';
import { PasswordInput, TextInput } from '@mantine/core';
import Alert from './Alert';

interface Props extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  hint?: string;
}

export const Field = forwardRef<HTMLInputElement, Props>(function Field({ label, icon: Icon, hint, id, className = '', type, size: _size, ...rest }, ref) {
  const generated = useId();
  const props = { ...rest, ref, id: id || generated, label, description: hint,
    className, leftSection: Icon ? <Icon size={17} /> : undefined,
    classNames: { input: 'us-field-input', label: 'us-field-label', description: 'us-field-hint' } };
  return type === 'password'
    ? <PasswordInput {...props} visibilityToggleButtonProps={{ 'aria-label': 'Mostrar u ocultar contraseña' }} />
    : <TextInput {...props} type={type} />;
});

export function ErrorNote({ children }: { children: React.ReactNode }) {
  return <Alert tono="danger">{children}</Alert>;
}
