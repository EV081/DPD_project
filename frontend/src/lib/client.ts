import axios from 'axios';

export const TOKEN_KEY = 'urbansafe_token';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://backend-urbansafe.onrender.com/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const errorMessage = (error: any, fallback: string): string =>
  error?.response?.data?.error || (error?.response ? fallback : 'No se pudo comunicar con el servidor.');

// Cuenta y perfil
export const updateProfileApi = async (name?: string, email?: string) =>
  (await api.put('/auth/me', { name, email })).data;

export const updatePasswordApi = async (current_password: string, new_password: string) =>
  (await api.put('/auth/me/password', { current_password, new_password })).data;

export const deleteAccountApi = async () => (await api.delete('/auth/me')).data;
