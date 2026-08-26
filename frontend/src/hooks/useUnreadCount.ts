import { useQuery } from '@tanstack/react-query';
import { getUnreadCount } from '../api/notifications';

export function useUnreadCount() {
  return useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: getUnreadCount,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}
