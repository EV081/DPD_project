'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { User, KeyRound, Trash2, LogOut, ChevronRight, Palette } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { updateProfileApi, updatePasswordApi, deleteAccountApi, errorMessage } from '@/lib/client';
import { ThemeSelector } from '@/components/ThemeToggle';
import { Field, ErrorNote } from '@/components/Field';
import { Spinner } from '@/components/Spinner';

type Modal = 'profile' | 'password' | 'delete' | null;

const iniciales = (name?: string) =>
  (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join('');

export default function AccountPage() {
  const { user, setUser, logout } = useAuth();
  const router = useRouter();
  const [modal, setModal] = useState<Modal>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    if (user) { setName(user.name || ''); setEmail(user.email || ''); }
  }, [user]);

  // Cerrar el diálogo con Escape
  useEffect(() => {
    if (!modal) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setModal(null);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [modal]);

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const open = (m: Modal) => { setError(null); setSuccess(null); setModal(m); };

  const run = async (fn: () => Promise<void>, fallback: string) => {
    setLoading(true);
    setError(null);
    try {
      await fn();
    } catch (err: any) {
      setError(errorMessage(err, fallback));
    } finally {
      setLoading(false);
    }
  };

  const saveProfile = () => {
    if (!name.trim() || !email.trim()) return setError('Ingresa un nombre y un correo válidos.');
    run(async () => {
      const res = await updateProfileApi(name, email);
      setUser(res.user || { ...user!, name, email });
      setSuccess(res.message || 'Perfil actualizado correctamente.');
      setModal(null);
    }, 'No se pudo actualizar el perfil.');
  };

  const savePassword = () => {
    if (!currentPassword || !newPassword) return setError('Ingresa la contraseña actual y la nueva.');
    if (newPassword.length < 6) return setError('La nueva contraseña debe tener al menos 6 caracteres.');
    run(async () => {
      const res = await updatePasswordApi(currentPassword, newPassword);
      setCurrentPassword(''); setNewPassword('');
      setSuccess(res.message || 'Contraseña actualizada correctamente.');
      setModal(null);
    }, 'No se pudo actualizar la contraseña.');
  };

  const deleteAccount = () => run(async () => { await deleteAccountApi(); handleLogout(); }, 'No se pudo eliminar la cuenta.');

  const row = 'flex w-full items-center justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-surface-2';

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-6 md:px-8 md:py-10">
      <h1 className="text-2xl font-bold tracking-tight text-fg">Mi cuenta</h1>

      <section className="card mt-6 flex items-center gap-4 p-5" aria-label="Perfil">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-brand-soft text-lg font-bold text-brand">
          {iniciales(user?.name)}
        </span>
        <div className="min-w-0">
          <p className="truncate text-lg font-semibold text-fg">{user?.name}</p>
          <p className="truncate text-sm text-muted">{user?.email}</p>
        </div>
      </section>

      {success && (
        <p role="status" className="mt-4 rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-3.5 py-2.5 text-sm text-emerald-800 dark:text-emerald-300">{success}</p>
      )}

      <h2 className="eyebrow mb-2 mt-8 px-1">Apariencia</h2>
      <section className="card p-5" aria-label="Apariencia">
        <p className="mb-3 flex items-center gap-2 text-sm text-muted"><Palette size={16} /> Elige el tema de la aplicación.</p>
        <ThemeSelector />
      </section>

      <h2 className="eyebrow mb-2 mt-8 px-1">Seguridad y perfil</h2>
      <section className="card divide-y divide-line overflow-hidden">
        <button onClick={() => open('profile')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-fg"><User size={18} className="text-muted" /> Editar datos personales</span>
          <ChevronRight size={17} className="text-muted" />
        </button>
        <button onClick={() => open('password')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-fg"><KeyRound size={18} className="text-muted" /> Cambiar contraseña</span>
          <ChevronRight size={17} className="text-muted" />
        </button>
        <button onClick={() => open('delete')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-rose-600 dark:text-rose-400"><Trash2 size={18} /> Eliminar cuenta</span>
          <ChevronRight size={17} className="text-muted" />
        </button>
      </section>

      <button onClick={handleLogout} className="btn btn-secondary mt-6 w-full !py-3">
        <LogOut size={17} /> Cerrar sesión
      </button>

      {modal && (
        <div className="fixed inset-0 z-[2000] flex items-end justify-center bg-slate-950/60 p-4 backdrop-blur-sm sm:items-center" onClick={() => setModal(null)}>
          <div role="dialog" aria-modal="true" className="float-panel w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            {modal === 'profile' && (
              <>
                <h3 className="text-lg font-semibold text-fg">Editar datos personales</h3>
                <div className="mt-5 space-y-4">
                  <Field label="Nombre completo" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
                  <Field label="Correo electrónico" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
              </>
            )}
            {modal === 'password' && (
              <>
                <h3 className="text-lg font-semibold text-fg">Cambiar contraseña</h3>
                <div className="mt-5 space-y-4">
                  <Field label="Contraseña actual" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} autoComplete="current-password" autoFocus />
                  <Field label="Nueva contraseña" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} autoComplete="new-password" hint="Mínimo 6 caracteres." />
                </div>
              </>
            )}
            {modal === 'delete' && (
              <>
                <h3 className="text-lg font-semibold text-fg">¿Eliminar tu cuenta?</h3>
                <p className="mt-2 text-sm text-muted">Esta acción no se puede deshacer. Tus datos se borrarán del sistema.</p>
              </>
            )}

            {error && <div className="mt-4"><ErrorNote>{error}</ErrorNote></div>}

            <div className="mt-6 flex gap-3">
              <button onClick={() => setModal(null)} className="btn btn-secondary flex-1">Cancelar</button>
              {modal === 'delete' ? (
                <button onClick={deleteAccount} disabled={loading} className="btn flex-1 bg-rose-600 text-white hover:bg-rose-700">
                  {loading ? <Spinner size={16} className="!text-white" /> : 'Sí, eliminar'}
                </button>
              ) : (
                <button onClick={modal === 'profile' ? saveProfile : savePassword} disabled={loading} className="btn btn-primary flex-1">
                  {loading ? <Spinner size={16} className="!text-current" /> : modal === 'profile' ? 'Guardar' : 'Actualizar'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
