'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Mail, Lock, ArrowRight } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { errorMessage } from '@/lib/client';
import { AuthShell } from '@/components/AuthShell';
import { Field, ErrorNote } from '@/components/Field';
import { Spinner } from '@/components/Spinner';

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return setError('Ingresa tu correo y contraseña.');
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      router.replace('/map');
    } catch (err: any) {
      setError(err?.response?.status === 401 ? 'El correo o la contraseña son incorrectos.' : errorMessage(err, 'Ocurrió un error inesperado.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell>
      <h2 className="text-2xl font-bold tracking-tight text-fg">Inicia sesión</h2>
      <p className="mt-1.5 text-sm text-muted">Accede para planificar rutas y consultar el aforo en tiempo real.</p>

      <form onSubmit={submit} className="mt-8 space-y-4" noValidate>
        <Field label="Correo electrónico" icon={Mail} type="email" autoComplete="email" value={email}
          onChange={(e) => setEmail(e.target.value)} placeholder="usuario@utec.edu.pe" />
        <Field label="Contraseña" icon={Lock} type="password" autoComplete="current-password" value={password}
          onChange={(e) => setPassword(e.target.value)} placeholder="Tu contraseña" />

        {error && <ErrorNote>{error}</ErrorNote>}

        <button type="submit" disabled={loading} className="btn btn-primary w-full !py-3">
          {loading ? <Spinner size={18} className="!text-current" /> : <>Entrar <ArrowRight size={17} /></>}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        ¿No tienes una cuenta?{' '}
        <Link href="/register" className="font-semibold text-brand hover:underline">Regístrate</Link>
      </p>
    </AuthShell>
  );
}
