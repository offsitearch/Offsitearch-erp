import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Megaphone, Pencil, Pin, Plus, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { createNotice, deleteNotice, getNotices, updateNotice } from '../../api/notices';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { EmptyState } from '../../components/ui/EmptyState';
import { LogoLoader } from '../../components/LogoLoader';
import DatePicker from '../../components/ui/DatePicker';
import { useToast } from '../../components/Toast';
import { noticeImportanceMeta, canAccess } from '../../lib/constants';
import { formatDate } from '../../lib/date';
import type { Notice, NoticeImportance, NoticeInput } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { inputClass, selectClass, primaryBtnClass, secondaryBtnClass, modalLabelClass } from '../../lib/styles';
import { useTranslation } from 'react-i18next';

export default function NoticeBoardPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const isAdmin = canAccess(user?.org_level_code, 'L2');
  const [modal, setModal] = useState<{ editing?: Notice } | null>(null);
  const [deleting, setDeleting] = useState<Notice | null>(null);

  const notices = useQuery({
    queryKey: ['notices', isAdmin],
    queryFn: () => getNotices({ include_inactive: isAdmin }),
  });

  const toggleActive = useMutation({
    mutationFn: (notice: Notice) => updateNotice(notice.id, { is_active: !notice.is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notices'] });
      toast(t('settings.noticeUpdated'), 'success');
    },
    onError: () => toast('Failed to update notice', 'error'),
  });

  const remove = useMutation({
    mutationFn: () => deleteNotice(deleting!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notices'] });
      toast(t('settings.noticeDeleted'), 'success');
      setDeleting(null);
    },
    onError: () => toast('Failed to delete notice', 'error'),
  });

  const sorted = [...(notices.data ?? [])].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t('nav.notices')}</h1>
           <p className="mt-1 text-sm text-muted">{t('notices.subtitle')}</p>
        </div>
        {isAdmin && (
          <button onClick={() => setModal({})} className={primaryBtnClass}>
            <Plus className="h-4 w-4" /> {t('settings.postNotice')}
          </button>
        )}
      </div>

      {notices.isPending ? (
        <LogoLoader />
      ) : sorted.length === 0 ? (
        <EmptyState
          title={t('settings.noNoticesYet')}
          text={t('settings.postFirstNotice')}
          icon={Megaphone}
        />
      ) : (
        <div className="space-y-3">
          {sorted.map((n) => {
            const meta = noticeImportanceMeta(n.importance);
            return (
              <div
                key={n.id}
                className={`rounded-xl border bg-surface p-5 shadow-card ${
                  n.is_pinned
                    ? 'border-orange/40 ring-1 ring-orange/20'
                    : 'border-border'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    {n.is_pinned && (
                      <Pin className="mt-1 h-4 w-4 shrink-0 fill-orange/60 text-orange" />
                    )}
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-base font-bold text-ink">{n.title}</h2>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${meta.badge}`}>
                          {meta.label}
                        </span>
                        {!n.is_active && isAdmin && (
                          <span className="rounded-full bg-surfaceWarm px-2 py-0.5 text-xs font-medium text-muted">
                            Inactive
                          </span>
                        )}
                      </div>
                      {n.body && <p className="mt-2 text-sm text-muted">{n.body}</p>}
                      <p className="mt-3 text-xs text-muted">
                        Posted {formatDate(n.created_at)}
                        {n.expiry_date ? ` · Expires ${formatDate(n.expiry_date)}` : ''}
                      </p>
                    </div>
                  </div>
                  {isAdmin && (
                    <div className="flex shrink-0 gap-1">
                      <button
                        onClick={() => setModal({ editing: n })}
                        className="rounded-lg p-1.5 text-muted transition hover:bg-surfaceWarm hover:text-ink"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setDeleting(n)}
                        aria-label="Delete notice"
                        className="rounded-lg p-1.5 text-muted transition hover:bg-dangerSoft hover:text-danger"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>
                {isAdmin && (
                  <button
                    onClick={() => toggleActive.mutate(n)}
                    className="mt-3 text-xs font-medium text-muted underline-offset-2 hover:text-navy hover:underline"
                  >
                    {n.is_active ? t('common.deactivate') : t('settings.activate')}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {modal && <NoticeModal notice={modal.editing} onClose={() => setModal(null)} />}
      {deleting && (
        <ConfirmDialog
          title={t('settings.deleteNotice')}
          message={`"${deleting.title}" will be permanently removed.`}
          confirmLabel={t('common.delete')}
          pending={remove.isPending}
          onConfirm={() => remove.mutate()}
          onClose={() => setDeleting(null)}
        />
      )}
    </div>
  );
}

function NoticeModal({ notice, onClose }: { notice?: Notice; onClose: () => void }) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<NoticeInput>({
    title: notice?.title ?? '',
    body: notice?.body ?? '',
    importance: notice?.importance ?? 'medium',
    is_pinned: notice?.is_pinned ?? false,
    publish_date: notice?.publish_date ?? '',
    expiry_date: notice?.expiry_date ?? '',
  });

  const save = useMutation({
    mutationFn: () => {
      const payload: NoticeInput = {
        ...form,
        publish_date: form.publish_date || null,
        expiry_date: form.expiry_date || null,
      };
      return notice ? updateNotice(notice.id, payload) : createNotice(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notices'] });
      toast(notice ? t('settings.noticeUpdated') : t('settings.noticePublished'), 'success');
      onClose();
    },
    onError: () => toast('Failed to save notice', 'error'),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-surface p-6 shadow-overlay">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink">{notice ? t('settings.editNotice') : t('settings.postNotice')}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-muted hover:bg-surfaceWarm">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <label className={modalLabelClass}>
            Title *
            <input
              required
              value={form.title}
              onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className={modalLabelClass}>
            Body
            <textarea
              rows={4}
              value={form.body ?? ''}
              onChange={(e) => setForm((p) => ({ ...p, body: e.target.value }))}
              className={`${inputClass} mt-1`}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className={modalLabelClass}>
              Importance
              <select
                value={form.importance}
                onChange={(e) => setForm((p) => ({ ...p, importance: e.target.value as NoticeImportance }))}
                className={`${selectClass} mt-1`}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label className={modalLabelClass}>
              Publish date
              <DatePicker
                value={form.publish_date ?? ''}
                onChange={(v) => setForm((p) => ({ ...p, publish_date: v }))}
                className="mt-1"
              />
            </label>
            <label className={modalLabelClass}>
              Expiry date
              <DatePicker
                value={form.expiry_date ?? ''}
                onChange={(v) => setForm((p) => ({ ...p, expiry_date: v }))}
                className="mt-1"
              />
            </label>
          </div>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={form.is_pinned}
              onChange={(e) => setForm((p) => ({ ...p, is_pinned: e.target.checked }))}
              className="rounded border-border"
            />
            Pin to top
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={save.isPending || !form.title}
              className={primaryBtnClass}
            >
              {notice ? t('common.save') : t('settings.publishNotice')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
