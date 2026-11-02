'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { User, KeyRound, Trash2, LogOut, ChevronRight, Palette } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { updateProfileApi, updatePasswordApi, deleteAccountApi, errorMessage } from '@/lib/client';
import { ThemeSelector } from '@/components/ThemeToggle';
import { Field, ErrorNote } from '@/components/Field';
import { Spinner } from '@/components/Spinner';
import Modal from '@/components/Modal';
import Alert from '@/components/Alert';
import MisReportes from '@/components/MisReportes';

type ModalKind = 'profile' | 'password' | 'delete' | null;

const iniciales = (name?: string) =>
  (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join('');

export default function AccountPage() {
  const { user, setUser, logout } = useAuth();
  const router = useRouter();
  const [modal, setModal] = useState<ModalKind>(null);
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

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const open = (m: ModalKind) => { setError(null); setSuccess(null); setModal(m); };

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
      <h1 className="text-3xl font-bold tracking-tight text-fg">Mi cuenta</h1>

      <section className="hero mt-6 flex items-center gap-4 p-6" aria-label="Perfil">
        <div className="pointer-events-none absolute -right-12 -top-12 h-44 w-44 rounded-full bg-white/20 blur-2xl" />
        <span className="relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-white/20 text-xl font-bold ring-2 ring-white/40">
          {iniciales(user?.name)}
        </span>
        <div className="relative min-w-0">
          <p className="truncate text-xl font-bold">{user?.name}</p>
          <p className="truncate text-sm text-white/80">{user?.email}</p>
        </div>
      </section>

      {success && <Alert tono="ok" className="mt-4">{success}</Alert>}

      <h2 className="eyebrow mb-2 mt-8 px-1">Apariencia</h2>
      <section className="card p-5" aria-label="Apariencia">
        <p className="mb-3 flex items-center gap-2 text-sm text-muted"><Palette size={16} /> Elige el tema de la aplicación.</p>
        <ThemeSelector />
      </section>

      <h2 className="eyebrow mb-2 mt-8 px-1">Mis reportes de seguridad</h2>
      <section className="card overflow-hidden" aria-label="Mis reportes">
        <MisReportes />
      </section>

      <h2 className="eyebrow mb-2 mt-8 px-1">Seguridad y perfil</h2>
      <section className="card divide-y divide-line overflow-hidden">
        <button onClick={() => open('profile')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-fg"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-muted"><User size={17} /></span> Editar datos personales</span>
          <ChevronRight size={17} className="text-muted" />
        </button>
        <button onClick={() => open('password')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-fg"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-muted"><KeyRound size={17} /></span> Cambiar contraseña</span>
          <ChevronRight size={17} className="text-muted" />
        </button>
        <button onClick={() => open('delete')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-danger"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-danger/12"><Trash2 size={17} /></span> Eliminar cuenta</span>
          <ChevronRight size={17} className="text-muted" />
        </button>
      </section>

      <button onClick={handleLogout} className="btn btn-secondary mt-6 w-full !py-3">
        <LogOut size={17} /> Cerrar sesión
      </button>

      {modal && (
        <Modal title={modal === 'profile' ? 'Editar datos personales' : modal === 'password' ? 'Cambiar contraseña' : '¿Eliminar tu cuenta?'} onClose={() => setModal(null)}>
          {modal === 'profile' && (
            <div className="space-y-4">
              <Field label="Nombre completo" value={name} onChange={(e) => setName(e.target.value)} />
              <Field label="Correo electrónico" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
          )}
          {modal === 'password' && (
            <div className="space-y-4">
              <Field label="Contraseña actual" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} autoComplete="current-password" />
              <Field label="Nueva contraseña" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} autoComplete="new-password" hint="Mínimo 6 caracteres." />
            </div>
          )}
          {modal === 'delete' && <p className="text-sm text-muted">Esta acción no se puede deshacer. Tus datos se borrarán del sistema.</p>}

          {error && <div className="mt-4"><ErrorNote>{error}</ErrorNote></div>}

          <div className="mt-6 flex gap-3">
            <button onClick={() => setModal(null)} className="btn btn-secondary flex-1">Cancelar</button>
            {modal === 'delete' ? (
              <button onClick={deleteAccount} disabled={loading} className="btn btn-sos flex-1">
                {loading ? <Spinner size={16} className="!text-white" /> : 'Sí, eliminar'}
              </button>
            ) : (
              <button onClick={modal === 'profile' ? saveProfile : savePassword} disabled={loading} className="btn btn-primary flex-1">
                {loading ? <Spinner size={16} className="!text-current" /> : modal === 'profile' ? 'Guardar' : 'Actualizar'}
              </button>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
