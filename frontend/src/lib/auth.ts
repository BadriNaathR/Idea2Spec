export interface AuthUser {
  id: string;
  username: string;
  role: 'business_analyst' | 'reviewer';
  full_name: string;
}

export const getUser = (): AuthUser | null => {
  const raw = localStorage.getItem('auth_user');
  return raw ? JSON.parse(raw) : null;
};

export const setUser = (user: AuthUser) => {
  localStorage.setItem('auth_user', JSON.stringify(user));
};

export const clearUser = () => {
  localStorage.removeItem('auth_user');
};

export const isBA = () => getUser()?.role === 'business_analyst';
export const isReviewer = () => getUser()?.role === 'reviewer';
