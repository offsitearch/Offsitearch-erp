import type { LeaveStatus } from '../../../lib/types';
import { leaveStatusMeta } from '../../../lib/constants';

export function LeaveStatusBadge({ status }: { status: LeaveStatus }) {
  const meta = leaveStatusMeta(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.badge}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  );
}
