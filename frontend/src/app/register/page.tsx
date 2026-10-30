'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { User, Mail, Lock } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { errorMessage } from '@/lib/client';
import { AuthShell } from '@/components/AuthShell';
import { Field, ErrorNote } from '@/components/Field';
import { Spinner } from '@/components/Spinner';

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) return setError('Completa todos los campos.');
    if (password.length < 6) return setError('La contraseña debe tener al menos 6 caracteres.');
    setLoading(true);
    setError(null);
    try {
      await register(name, email, password);
      router.replace('/map');
    } catch (err: any) {
      setError(errorMessage(err, err?.response?.status === 409 ? 'Ese correo ya está en uso.' : 'Error al registrarse.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell>
      <h2 className="text-2xl font-bold tracking-tight text-fg">Crea tu cuenta</h2>
      <p className="mt-1.5 text-sm text-muted">Es gratis y toma menos de un minuto.</p>

      <form onSubmit={submit} className="mt-8 space-y-4" noValidate>
        <Field label="Nombre completo" icon={User} value={name} onChange={(e) => setName(e.target.value)}
          autoComplete="name" placeholder="Ej. Alessandro Monzón" />
        <Field label="Correo electrónico" icon={Mail} type="email" value={email} onChange={(e) => setEmail(e.target.value)}
          autoComplete="email" placeholder="usuario@utec.edu.pe" />
        <Field label="Contraseña" icon={Lock} type="password" value={password} onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password" placeholder="Mínimo 6 caracteres" hint="Usa al menos 6 caracteres." />

        {error && <ErrorNote>{error}</ErrorNote>}

        <button type="submit" disabled={loading} className="btn btn-primary w-full !py-3">
          {loading ? <Spinner size={18} className="!text-current" /> : 'Crear cuenta'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        ¿Ya tienes una cuenta?{' '}
        <Link href="/login" className="font-semibold text-brand hover:underline">Inicia sesión</Link>
      </p>
    </AuthShell>
  );
}
