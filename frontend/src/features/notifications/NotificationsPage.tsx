import { useState } from 'react';
import type { KeyboardEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bell,
  CalendarDays,
  CheckCheck,
  ListTodo,
  Loader2,
  MailOpen,
  Palmtree,
  Trash2,
} from 'lucide-react';
import {
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../api/notifications';
import { EmptyState } from '../../components/ui/EmptyState';
import { LogoLoader } from '../../components/LogoLoader';
import type { Notification } from '../../lib/types';
import { useTranslation } from 'react-i18next';

function typeMeta(type: string): { icon: typeof Bell; tint: string } {
  switch (type) {
    case 'leave':
      return { icon: Palmtree, tint: 'bg-warningSoft text-warning' };
    case 'task':
      return { icon: ListTodo, tint: 'bg-infoSoft text-info' };
    case 'meeting':
      return { icon: CalendarDays, tint: 'bg-navy/10 text-navy' };
    default:
      return { icon: Bell, tint: 'bg-orange/10 text-orange' };
  }
}

function relativeTime(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

type Filter = 'all' | 'unread';

export default function NotificationsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<Filter>('all');

  const notifications = useQuery({ queryKey: ['notifications'], queryFn: getNotifications });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
    queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] });
  };

  const markOne = useMutation({
    mutationFn: (id: number) => markNotificationRead(id),
    onSuccess: invalidateAll,
  });

  const markAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidateAll,
  });

  const removeOne = useMutation({
    mutationFn: (id: number) => deleteNotification(id),
    onSuccess: invalidateAll,
  });

  const list = notifications.data ?? [];
  const unread = list.filter((n) => !n.read_at).length;
  const visible = filter === 'unread' ? list.filter((n) => !n.read_at) : list;

  /** Clicking a notification only marks it read — links are not navigated. */
  const open = (n: Notification) => {
    if (!n.read_at) markOne.mutate(n.id);
  };

  const openOnKey = (e: KeyboardEvent, n: Notification) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      open(n);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{t('notifications.title')}</h1>
          <p className="mt-1 text-sm text-graphite">
            {unread > 0 ? t('notifications.unreadCount', { count: unread }) : 'You’re all caught up'}
          </p>
        </div>
        {unread > 0 && (
          <button
            onClick={() => markAll.mutate()}
            disabled={markAll.isPending}
            className="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium text-navy transition hover:bg-surfaceWarm hover:text-orange focus:outline-none focus:ring-2 focus:ring-orange/40 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {markAll.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCheck className="h-4 w-4" />
            )}
            {t('notifications.markAllRead')}
          </button>
        )}
      </div>

      <div className="flex rounded-lg border border-border bg-surface p-1">
        {(['all', 'unread'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`flex-1 rounded-md px-4 py-1.5 text-sm font-medium transition ${
              filter === f ? 'bg-navy text-white' : 'text-graphite hover:text-ink'
            }`}
          >
            {f === 'all' ? 'All' : `Unread${unread > 0 ? ` (${unread})` : ''}`}
          </button>
        ))}
      </div>

      {notifications.isPending ? (
        <LogoLoader />
      ) : list.length === 0 ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <EmptyState
            icon={Bell}
            title={t('notifications.noNotifications')}
            text={t('notifications.notificationsWillAppear')}
          />
        </div>
      ) : visible.length === 0 ? (
        <div className="rounded-lg border border-border bg-surface p-4">
          <EmptyState
            icon={MailOpen}
            title={t('notifications.noUnreadNotifications')}
            text="Everything has been read. You’re all caught up."
          />
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <div className="divide-y divide-border">
            {visible.map((n) => {
              const meta = typeMeta(n.type);
              const Icon = meta.icon;
              const isUnread = !n.read_at;
              return (
                <div
                  key={n.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => open(n)}
                  onKeyDown={(e) => openOnKey(e, n)}
                  className={`group flex w-full cursor-pointer items-start gap-3 px-4 py-4 text-left transition ${
                    isUnread ? 'bg-surface hover:bg-surfaceWarm' : 'bg-surfaceWarm/50 hover:bg-surfaceWarm'
                  }`}
                >
                  <span
                    className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md transition ${
                      isUnread ? meta.tint : 'bg-graphite/10 text-graphite'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span
                      className={`block text-sm ${isUnread ? 'font-semibold text-ink' : 'font-medium text-ink'}`}
                    >
                      {n.title}
                    </span>
                    {n.body && <span className="mt-0.5 block text-sm text-graphite">{n.body}</span>}
                    <span className="mt-1 block text-xs text-muted">{relativeTime(n.created_at)}</span>
                  </span>
                  {isUnread && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-orange" />}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeOne.mutate(n.id);
                    }}
                    disabled={removeOne.isPending}
                    title={t('common.delete')}
                    aria-label={t('common.delete')}
                    className="mt-0.5 shrink-0 rounded-md p-1.5 text-muted transition hover:bg-dangerSoft hover:text-danger focus:outline-none focus:ring-2 focus:ring-danger/40 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {removeOne.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
