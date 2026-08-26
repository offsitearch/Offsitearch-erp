import { useMutation, useQueryClient } from '@tanstack/react-query';
import { login, logout } from '../api/auth';
import { useAuthStore } from '../store/authStore';

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);
  return useMutation({
    mutationFn: ({ userId, password }: { userId: string; password: string }) =>
      login(userId, password),
    onSuccess: (data) => setAuth(data),
  });
}

export function useLogout() {
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => {
      if (!refreshToken) return Promise.resolve();
      return logout(refreshToken);
    },
    onSettled: () => {
      queryClient.clear();
      clearAuth();
    },
  });
}
