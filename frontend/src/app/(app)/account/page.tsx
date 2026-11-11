'use client';

import { useEffect, useState, memo } from 'react';
import { useRouter } from 'next/navigation';
import { User, KeyRound, Trash2, LogOut, ChevronRight, Palette, MapPin } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useAuth } from '@/context/AuthContext';
import { updateProfileApi, updatePasswordApi, deleteAccountApi, errorMessage } from '@/lib/client';
import { ThemeSelector } from '@/components/ThemeToggle';
import { Field, ErrorNote } from '@/components/Field';
import { Spinner } from '@/components/Spinner';
import Modal from '@/components/Modal';
import Alert from '@/components/Alert';
import MisReportes from '@/components/MisReportes';
import { getUserLocation } from '@/lib/geolocation';

// Carga dinámica del MiniMapa sin SSR para la ubicación del usuario
const MiniMap = dynamic(() => import('@/components/MiniMap'), {
  ssr: false,
  loading: () => <div className="h-48 w-full animate-pulse rounded-2xl bg-surface-2" />,
});

type ModalKind = 'profile' | 'password' | 'delete' | null;

const iniciales = (name?: string) =>
  (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join('');

// --- MODAL 1: EDITAR PERFIL (Estado aislado para no perder foco) ---
function ProfileModal({
  initialName,
  initialEmail,
  onClose,
  onSuccess,
}: {
  initialName: string;
  initialEmail: string;
  onClose: () => void;
  onSuccess: (msg: string, updatedUser: any) => void;
}) {
  const [name, setName] = useState(initialName);
  const [email, setEmail] = useState(initialEmail);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return setError('Ingresa un nombre y un correo válidos.');
    setLoading(true);
    setError(null);
    try {
      const res = await updateProfileApi(name, email);
      onSuccess(res.message || 'Perfil actualizado correctamente.', res.user || { name, email });
    } catch (err: any) {
      setError(errorMessage(err, 'No se pudo actualizar el perfil.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Editar datos personales" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Nombre completo" value={name} onChange={(e) => setName(e.target.value)} />
        <Field label="Correo electrónico" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />

        {error && <ErrorNote>{error}</ErrorNote>}

        <div className="mt-6 flex gap-3 pt-2">
          <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
            Cancelar
          </button>
          <button type="submit" disabled={loading} className="btn btn-primary flex-1">
            {loading ? <Spinner size={16} className="!text-current" /> : 'Guardar'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// --- MODAL 2: CAMBIAR CONTRASEÑA (Estado aislado) ---
function PasswordModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword) return setError('Ingresa la contraseña actual y la nueva.');
    if (newPassword.length < 6) return setError('La nueva contraseña debe tener al menos 6 caracteres.');
    setLoading(true);
    setError(null);
    try {
      const res = await updatePasswordApi(currentPassword, newPassword);
      onSuccess(res.message || 'Contraseña actualizada correctamente.');
    } catch (err: any) {
      setError(errorMessage(err, 'No se pudo actualizar la contraseña.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Cambiar contraseña" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field
          label="Contraseña actual"
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          autoComplete="current-password"
        />
        <Field
          label="Nueva contraseña"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          autoComplete="new-password"
          hint="Mínimo 6 caracteres."
        />

        {error && <ErrorNote>{error}</ErrorNote>}

        <div className="mt-6 flex gap-3 pt-2">
          <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
            Cancelar
          </button>
          <button type="submit" disabled={loading} className="btn btn-primary flex-1">
            {loading ? <Spinner size={16} className="!text-current" /> : 'Actualizar'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// --- PÁGINA PRINCIPAL ---
export default function AccountPage() {
  const { user, setUser, logout } = useAuth();
  const router = useRouter();
  const [modal, setModal] = useState<ModalKind>(null);
  const [loadingDelete, setLoadingDelete] = useState(false);
  const [errorDelete, setErrorDelete] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Estado de geolocalización para el mini mapa
  const [coords, setCoords] = useState<{ latitude: number; longitude: number } | null>(null);
  const [locationError, setLocationError] = useState(false);

  // Obtener la ubicación actual del dispositivo
  useEffect(() => {
    let active = true;
    getUserLocation()
      .then((position) => {
        if (active) setCoords({ latitude: position.lat, longitude: position.lon });
      })
      .catch(() => { if (active) setLocationError(true); });
    return () => { active = false; };
  }, []);

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const open = (m: ModalKind) => {
    setSuccess(null);
    setErrorDelete(null);
    setModal(m);
  };

  const deleteAccount = async () => {
    setLoadingDelete(true);
    setErrorDelete(null);
    try {
      await deleteAccountApi();
      handleLogout();
    } catch (err: any) {
      setErrorDelete(errorMessage(err, 'No se pudo eliminar la cuenta.'));
    } finally {
      setLoadingDelete(false);
    }
  };

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
        <p className="mb-3 flex items-center gap-2 text-sm text-muted">
          <Palette size={16} /> Elige el tema de la aplicación.
        </p>
        <ThemeSelector />
      </section>

      <h2 className="eyebrow mb-2 mt-8 px-1">Mis reportes de seguridad</h2>
      <section className="card overflow-hidden" aria-label="Mis reportes">
        <MisReportes />
      </section>

      <h2 className="eyebrow mb-2 mt-8 px-1">Seguridad y perfil</h2>
      <section className="card divide-y divide-line overflow-hidden">
        <button onClick={() => open('profile')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-fg">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-muted">
              <User size={17} />
            </span>{' '}
            Editar datos personales
          </span>
          <ChevronRight size={17} className="text-muted" />
        </button>
        <button onClick={() => open('password')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-fg">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-muted">
              <KeyRound size={17} />
            </span>{' '}
            Cambiar contraseña
          </span>
          <ChevronRight size={17} className="text-muted" />
        </button>
        <button onClick={() => open('delete')} className={row}>
          <span className="flex items-center gap-3 text-sm font-medium text-danger">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-danger/12">
              <Trash2 size={17} />
            </span>{' '}
            Eliminar cuenta
          </span>
          <ChevronRight size={17} className="text-muted" />
        </button>
      </section>

      {/* --- MINI MAPA CON LA UBICACIÓN ACTUAL --- */}
      <h2 className="eyebrow mb-2 mt-8 px-1">Ubicación actual</h2>
      <section className="card p-5" aria-label="Ubicación actual">
        <p className="mb-3 flex items-center gap-2 text-sm text-muted">
          <MapPin size={16} className="text-brand" />
          {coords ? 'Ubicación obtenida desde tu dispositivo al abrir esta pantalla.' : locationError ? 'No se pudo obtener tu ubicación. No mostramos un punto de referencia como si fuera tu posición.' : 'Consultando la ubicación de tu dispositivo…'}
        </p>
        <div className="overflow-hidden rounded-2xl border border-line shadow-sm">
          {coords ? (
            <MiniMap
              latitude={coords.latitude}
              longitude={coords.longitude}
              stationName="Tu ubicación"
              systemColor="#2563eb"
            />
          ) : (
            <div className="h-48 w-full flex items-center justify-center bg-surface-2 text-sm text-muted">
              {locationError ? 'Ubicación no disponible. Revisa los permisos del navegador.' : 'Obteniendo ubicación…'}
            </div>
          )}
        </div>
      </section>

      <button onClick={handleLogout} className="btn btn-secondary mt-6 w-full !py-3">
        <LogOut size={17} /> Cerrar sesión
      </button>

      {/* RENDERIZADO DE MODALES AISLADOS */}
      {modal === 'profile' && (
        <ProfileModal
          initialName={user?.name || ''}
          initialEmail={user?.email || ''}
          onClose={() => setModal(null)}
          onSuccess={(msg, updatedUser) => {
            setUser({ ...user!, ...updatedUser });
            setSuccess(msg);
            setModal(null);
          }}
        />
      )}

      {modal === 'password' && (
        <PasswordModal
          onClose={() => setModal(null)}
          onSuccess={(msg) => {
            setSuccess(msg);
            setModal(null);
          }}
        />
      )}

      {modal === 'delete' && (
        <Modal title="¿Eliminar tu cuenta?" onClose={() => setModal(null)}>
          <p className="text-sm text-muted">Esta acción no se puede deshacer. Tus datos se borrarán del sistema.</p>
          {errorDelete && (
            <div className="mt-4">
              <ErrorNote>{errorDelete}</ErrorNote>
            </div>
          )}
          <div className="mt-6 flex gap-3">
            <button onClick={() => setModal(null)} className="btn btn-secondary flex-1">
              Cancelar
            </button>
            <button onClick={deleteAccount} disabled={loadingDelete} className="btn btn-sos flex-1">
              {loadingDelete ? <Spinner size={16} className="!text-white" /> : 'Sí, eliminar'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}