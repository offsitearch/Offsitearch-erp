import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { canAccess } from '../lib/constants';
import { useAuthStore } from '../store/authStore';

export function RequireAuth() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const location = useLocation();

  if (!accessToken) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

export function RequireRole({ minLevel }: { minLevel: string }) {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  if (!canAccess(user?.org_level_code, minLevel)) {
    return <Navigate to="/dashboard" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
