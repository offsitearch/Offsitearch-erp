import { timesheetStatusMeta } from '../../../lib/constants';
import type { TimesheetStatus } from '../../../lib/types';

export function TimesheetStatusBadge({ status }: { status: TimesheetStatus }) {
  const meta = timesheetStatusMeta(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${meta.badge}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  );
}
