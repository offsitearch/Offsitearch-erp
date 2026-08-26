import type { AttendanceRecord, Holiday } from '../../../lib/types';
import { ATTENDANCE_STATUS_META } from '../../../lib/constants';
import { buildMonthGrid, formatTime, toISODate, WEEKDAYS } from '../../../lib/date';

interface MonthCalendarProps {
  year: number;
  month: number;
  records: AttendanceRecord[];
  holidays: Holiday[];
  selectedDate?: string | null;
  onSelectDay?: (date: string) => void;
}

const MAX_STATUS_ROWS = 3;

export function MonthCalendar({
  year,
  month,
  records,
  holidays,
  selectedDate,
  onSelectDay,
}: MonthCalendarProps) {
  const cells = buildMonthGrid(year, month);
  const todayISO = toISODate(new Date());
  const recordsByDate = new Map(records.map((r) => [r.date, r]));
  const holidaysByDate = new Map(holidays.map((h) => [h.date, h]));

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <div className="overflow-x-auto">
        <div className="min-w-[560px]">
          <div className="grid grid-cols-7 border-b border-border">
            {WEEKDAYS.map((day) => (
              <div
                key={day}
                className="px-1 py-2 text-center text-[11px] font-semibold uppercase tracking-wider text-muted"
              >
                {day}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
        {cells.map(({ date, inMonth }, index) => {
          const iso = toISODate(date);
          const record = recordsByDate.get(iso);
          const holiday = holidaysByDate.get(iso);
          const isWeekend = date.getDay() === 0 || date.getDay() === 6;
          const isToday = iso === todayISO;
          const isSelected = iso === selectedDate;
          const clickable = Boolean(onSelectDay && inMonth);

          const statusRows = record
            ? [
                {
                  meta: ATTENDANCE_STATUS_META[record.status],
                  detail: record.check_in_time ? formatTime(record.check_in_time) : null,
                },
              ]
            : [];
          const visible = statusRows.slice(0, MAX_STATUS_ROWS);
          const more = statusRows.length - visible.length;

          const cellClass = [
            'relative min-h-[5.25rem] border-r border-b border-border p-1.5 text-left transition',
            index % 7 === 6 ? 'border-r-0' : '',
            index >= 35 ? 'border-b-0' : '',
            !inMonth
              ? 'bg-paper/40'
              : isWeekend
                ? 'bg-surfaceWarm/40'
                : 'bg-surface',
            isToday ? 'bg-warningSoft/40' : '',
            isSelected ? 'bg-navy/5 ring-1 ring-inset ring-navy/40' : '',
            clickable
              ? 'cursor-pointer hover:bg-surfaceWarm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy'
              : 'cursor-default',
          ]
            .filter(Boolean)
            .join(' ');

          const content = (
            <>
              {isToday && (
                <span
                  aria-hidden="true"
                  className="absolute inset-x-0 top-0 h-0.5 rounded-t bg-orange"
                />
              )}
              <div className="flex items-start justify-between gap-1">
                <span
                  className={`inline-flex h-6 items-center justify-center text-xs font-medium ${
                    isToday ? 'font-bold text-ink' : !inMonth ? 'text-muted/40' : isWeekend ? 'text-muted/70' : 'text-ink'
                  }`}
                >
                  {date.getDate()}
                </span>
                {isToday && (
                  <span className="rounded-sm bg-orange/15 px-1.5 py-px text-[9px] font-bold uppercase tracking-wider text-orange">
                    Today
                  </span>
                )}
              </div>
              {holiday && inMonth && (
                <p
                  className="mt-1 truncate rounded-sm bg-surfaceWarm px-1 py-px text-[10px] font-medium text-muted"
                  title={holiday.name}
                >
                  {holiday.name}
                </p>
              )}
              {visible.map(({ meta, detail }, i) => (
                <div
                  key={i}
                  className="mt-1 flex items-center gap-1 truncate text-[10px]"
                  title={`${meta.label}${detail ? ` · ${detail}` : ''}`}
                >
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${meta.dot}`} />
                  <span className="truncate text-muted">
                    {meta.short}
                    {detail && <span className="tabular-nums"> · {detail}</span>}
                  </span>
                </div>
              ))}
              {more > 0 && <p className="mt-1 text-[10px] font-medium text-muted">+{more} more</p>}
            </>
          );

          if (clickable) {
            return (
              <button
                key={index}
                type="button"
                onClick={() => onSelectDay?.(iso)}
                className={cellClass}
                aria-pressed={isSelected}
                aria-current={isToday ? 'date' : undefined}
                aria-label={`${date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}${isToday ? ', today' : ''}${
                  record ? `, ${ATTENDANCE_STATUS_META[record.status].label}` : ''
                }`}
              >
                {content}
              </button>
            );
          }
          return (
            <div key={index} className={cellClass}>
              {content}
            </div>
          );
        })}
          </div>
        </div>
      </div>
    </div>
  );
}
