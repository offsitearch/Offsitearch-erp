import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CalendarDays,
  Check,
  Clock,
  Loader2,
  MapPin,
  Plus,
  Users,
  Video,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { createMeeting, deleteMeeting, getMeetings, rsvpMeeting, updateMeeting } from '../../api/meetings';
import { getUsers } from '../../api/settings';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { useToast } from '../../components/Toast';
import DatePicker from '../../components/ui/DatePicker';
import TimeInput from '../../components/ui/TimeInput';
import { MEETING_TYPE_OPTIONS, LEVEL_BADGE, meetingStatusMeta, meetingTypeLabel, canAccess } from '../../lib/constants';
import type { Meeting, MeetingInput, MeetingType, RsvpStatus, UserBrief } from '../../lib/types';
import { useAuthStore } from '../../store/authStore';
import { inputClass, selectClass, primaryBtnClass, secondaryBtnClass, dangerBtnClass, modalLabelClass } from '../../lib/styles';
import { toISODate } from '../../lib/date';
import { useTranslation } from 'react-i18next';

export default function MeetingsPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const canCreate = canAccess(user?.org_level_code, 'L3');
  const [creating, setCreating] = useState(false);

  const meetings = useQuery({ queryKey: ['meetings'], queryFn: getMeetings });

  const upcoming = (meetings.data ?? [])
    .filter((m) => m.status === 'scheduled')
    .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime());

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">{t('meetings.title')}</h1>
           <p className="mt-1 text-sm text-muted">{t('meetings.scheduleStudioSyncs')}, client reviews and site visits.</p>
        </div>
        {canCreate && (
          <button onClick={() => setCreating(true)} className={primaryBtnClass}>
            <Plus className="h-4 w-4" /> Schedule Meeting
          </button>
        )}
      </div>

      {meetings.isPending ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-52 w-full rounded-xl" />
          ))}
        </div>
      ) : upcoming.length === 0 ? (
        <EmptyState
          title={t('meetings.noUpcomingMeetings')}
          text={t('meetings.scheduledAppearHere')}
          icon={CalendarDays}
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {upcoming.map((m) => (
            <MeetingCard key={m.id} meeting={m} />
          ))}
        </div>
      )}

      {creating && <MeetingFormModal onClose={() => setCreating(false)} />}
    </div>
  );
}

function MeetingCard({ meeting }: { meeting: Meeting }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const canManage = canAccess(user?.org_level_code, 'L3') || meeting.organizer_id === user?.id;
  const [confirmDelete, setConfirmDelete] = useState(false);

  const respond = useMutation({
    mutationFn: (status: RsvpStatus) => rsvpMeeting(meeting.id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      toast('RSVP updated', 'success');
    },
    onError: (err) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast(detail ?? 'Failed to update RSVP', 'error');
    },
  });

  const markComplete = useMutation({
    mutationFn: () => updateMeeting(meeting.id, { status: 'completed' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      toast('Meeting marked complete', 'success');
    },
    onError: () => toast('Failed to update meeting', 'error'),
  });

  const remove = useMutation({
    mutationFn: () => deleteMeeting(meeting.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      toast('Meeting deleted', 'success');
    },
    onError: () => toast('Failed to delete meeting', 'error'),
  });

  const when = new Date(meeting.scheduled_at);
  const status = meetingStatusMeta(meeting.status);

  return (
    <div className="flex flex-col rounded-xl border border-border bg-surface p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex flex-col items-center rounded-lg bg-navy/10 px-3 py-2 text-navy">
            <span className="text-lg font-bold leading-none">
              {when.toLocaleDateString('en-IN', { day: '2-digit' })}
            </span>
            <span className="text-[10px] font-semibold uppercase">
              {when.toLocaleDateString('en-IN', { month: 'short' })}
            </span>
          </div>
          <div>
            <h3 className="font-bold text-ink">{meeting.title}</h3>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
              <span className="rounded-full bg-surfaceWarm px-2 py-0.5 font-medium text-graphite">
                {meetingTypeLabel(meeting.meeting_type)}
              </span>
              <span className={`rounded-full px-2 py-0.5 font-medium ${status.badge}`}>{status.label}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-1.5 text-sm text-muted">
        <p className="flex items-center gap-2">
          <Clock className="h-3.5 w-3.5" />
          {when.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })} · {meeting.duration_minutes} min
        </p>
        {meeting.location && (
          <p className="flex items-center gap-2">
            <MapPin className="h-3.5 w-3.5" /> {meeting.location}
          </p>
        )}
        {meeting.meeting_link && (
          <p className="flex items-center gap-2">
            <Video className="h-3.5 w-3.5" /> {meeting.meeting_link}
          </p>
        )}
        <p className="flex items-center gap-2">
          <Users className="h-3.5 w-3.5" />
          {meeting.attendees.length === 0
            ? 'No attendees yet'
            : `${meeting.attendees.length} attending · ${meeting.organizer_name ?? 'you'} (organizer)`}
        </p>
      </div>

      {meeting.description && (
        <p className="mt-3 rounded-lg bg-surfaceWarm px-3 py-2 text-sm text-muted">
          {meeting.description}
        </p>
      )}

      {meeting.my_rsvp && meeting.my_rsvp !== 'pending' && (
        <div className="mt-3 text-xs font-medium text-muted">
          You RSVP'd: <span className="capitalize">{meeting.my_rsvp}</span>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-3">
        {meeting.my_rsvp === 'pending' ? (
          <>
            <button
              onClick={() => respond.mutate('accepted')}
              disabled={respond.isPending}
              className="inline-flex h-8 items-center gap-1.5 rounded-md bg-success px-3 text-xs font-medium text-white transition hover:bg-success/90 disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" /> Accept
            </button>
            <button
              onClick={() => respond.mutate('declined')}
              disabled={respond.isPending}
              className={secondaryBtnClass}
              style={{ height: '32px', fontSize: '12px' }}
            >
              <X className="h-3.5 w-3.5" /> Decline
            </button>
          </>
        ) : (
          <span className="text-xs text-muted">RSVP sent</span>
        )}
        {canManage && meeting.status === 'scheduled' && (
          <button
            onClick={() => markComplete.mutate()}
            className={secondaryBtnClass}
            style={{ height: '32px', fontSize: '12px', marginLeft: 'auto' }}
          >
            Mark complete
          </button>
        )}
        {canManage && (
          <button
            onClick={() => setConfirmDelete(true)}
            className={dangerBtnClass}
            style={{ height: '32px', fontSize: '12px' }}
          >
            Cancel
          </button>
        )}
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title="Cancel meeting?"
          message={`"${meeting.title}" will be cancelled and removed.`}
          confirmLabel="Cancel meeting"
          pending={remove.isPending}
          onConfirm={() => {
            remove.mutate(undefined, {
              onSuccess: () => setConfirmDelete(false),
            });
          }}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </div>
  );
}

function MeetingFormModal({ onClose }: { onClose: () => void }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const users = useQuery({
    queryKey: ['meeting-attendees'],
    queryFn: () => getUsers({ active_only: true }),
    enabled: !!user,
    retry: false,
  });

  // scheduled_at holds the raw local "YYYY-MM-DDTHH:mm" while editing and is
  // converted to a UTC ISO string only on submit — datetime pickers must never
  // receive a "Z" suffixed value or they stop matching/persisting.
  const [form, setForm] = useState<MeetingInput>({
    title: '',
    description: '',
    meeting_type: 'internal',
    scheduled_at: '',
    duration_minutes: 60,
    location: '',
    meeting_link: '',
    attendee_ids: [],
  });

  const save = useMutation({
    mutationFn: () =>
      createMeeting({ ...form, scheduled_at: new Date(form.scheduled_at).toISOString() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      toast('Meeting scheduled', 'success');
      onClose();
    },
    onError: () => toast('Failed to schedule meeting', 'error'),
  });

  function set<K extends keyof MeetingInput>(key: K, value: MeetingInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleAttendee(id: number) {
    set(
      'attendee_ids',
      (form.attendee_ids ?? []).includes(id)
        ? (form.attendee_ids ?? []).filter((x) => x !== id)
        : [...(form.attendee_ids ?? []), id],
    );
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navyDark/40 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-surface p-6 shadow-overlay">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink">Schedule meeting</h2>
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
              onChange={(e) => set('title', e.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className={modalLabelClass}>
            Description
            <textarea
              rows={2}
              value={form.description ?? ''}
              onChange={(e) => set('description', e.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className={modalLabelClass}>
              Type
              <select
                value={form.meeting_type}
                onChange={(e) => set('meeting_type', e.target.value as MeetingType)}
                className={`${selectClass} mt-1`}
              >
                {MEETING_TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {meetingTypeLabel(t)}
                  </option>
                ))}
              </select>
            </label>
            <label className={modalLabelClass}>
              Duration (minutes)
              <input
                type="number"
                min={15}
                max={600}
                step={15}
                value={form.duration_minutes}
                onChange={(e) => set('duration_minutes', Number(e.target.value))}
                className={`${inputClass} mt-1`}
              />
            </label>
            <label className={modalLabelClass}>
              Date *
              <DatePicker
                value={form.scheduled_at.slice(0, 10)}
                onChange={(d) => set('scheduled_at', `${d}T${form.scheduled_at.slice(11, 16) || '10:00'}`)}
                className="mt-1"
              />
            </label>
            <label className={modalLabelClass}>
              Start time *
              <TimeInput
                value={form.scheduled_at.slice(11, 16)}
                onChange={(t) => set('scheduled_at', `${form.scheduled_at.slice(0, 10) || toISODate(new Date())}T${t}`)}
                className="mt-1"
              />
            </label>
            <label className={modalLabelClass}>
              Location
              <input
                value={form.location ?? ''}
                onChange={(e) => set('location', e.target.value)}
                className={`${inputClass} mt-1`}
              />
            </label>
          </div>
          <label className={modalLabelClass}>
            Video / meeting link
            <input
              value={form.meeting_link ?? ''}
              onChange={(e) => set('meeting_link', e.target.value)}
              className={`${inputClass} mt-1`}
              placeholder="https://…"
            />
          </label>

          <label className={modalLabelClass}>
            Attendees
            <div className="mt-1 max-h-28 space-y-1.5 overflow-y-auto rounded-md border border-border p-2">
              {(users.data ?? []).map((u: UserBrief) => (
                <label key={u.id} className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={(form.attendee_ids ?? []).includes(u.id)}
                    onChange={() => toggleAttendee(u.id)}
                    className="rounded border-border"
                  />
                  {u.name}
                  <span className="text-xs text-muted">{u.designation}</span>
                  {u.org_level_code && (
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase ${LEVEL_BADGE[u.org_level_code as keyof typeof LEVEL_BADGE] ?? 'bg-graphite/10 text-graphite'}`}>
                      {u.org_level_code}
                    </span>
                  )}
                </label>
              ))}
              {(users.data ?? []).length === 0 && !users.isPending && (
                <p className="text-sm text-muted">No employees available.</p>
              )}
            </div>
          </label>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className={secondaryBtnClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={save.isPending || !form.title || !form.scheduled_at}
              className={primaryBtnClass}
            >
              {save.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Schedule
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
