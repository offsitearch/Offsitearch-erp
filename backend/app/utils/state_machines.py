"""State machine transition guards for domain models."""

from app.utils.enums import (
    ExpenseStatus,
    LeaveStatus,
    MeetingStatus,
    PhaseStatus,
    ProjectStatus,
    SiteVisitStatus,
    TaskStatus,
    TimesheetStatus,
)
from app.utils.errors import (
    FinanceError,
    LeaveError,
    MeetingError,
    ProjectError,
    SiteVisitError,
    TaskError,
    TimesheetError,
)

# ── Allowed transitions: from_status → {set of valid target statuses} ──────

TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED},
    TaskStatus.IN_PROGRESS: {TaskStatus.REVIEW, TaskStatus.DONE, TaskStatus.BLOCKED},
    TaskStatus.REVIEW: {TaskStatus.IN_PROGRESS, TaskStatus.DONE},
    TaskStatus.BLOCKED: {TaskStatus.TODO, TaskStatus.IN_PROGRESS},
    TaskStatus.DONE: set(),
}

PHASE_TRANSITIONS: dict[PhaseStatus, set[PhaseStatus]] = {
    PhaseStatus.NOT_STARTED: {PhaseStatus.IN_PROGRESS},
    PhaseStatus.IN_PROGRESS: {PhaseStatus.COMPLETED, PhaseStatus.DELAYED},
    PhaseStatus.DELAYED: {PhaseStatus.IN_PROGRESS},
    PhaseStatus.COMPLETED: set(),
}

PROJECT_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.DRAFT: {ProjectStatus.CONCEPT, ProjectStatus.ON_HOLD, ProjectStatus.CANCELLED},
    ProjectStatus.CONCEPT: {ProjectStatus.DESIGN, ProjectStatus.ON_HOLD, ProjectStatus.CANCELLED},
    ProjectStatus.DESIGN: {
        ProjectStatus.UNDER_REVIEW,
        ProjectStatus.ON_HOLD,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.UNDER_REVIEW: {
        ProjectStatus.IN_CONSTRUCTION,
        ProjectStatus.ON_HOLD,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.IN_CONSTRUCTION: {
        ProjectStatus.COMPLETED,
        ProjectStatus.ON_HOLD,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.ON_HOLD: {ProjectStatus.DRAFT, ProjectStatus.CANCELLED},
    ProjectStatus.COMPLETED: set(),
    ProjectStatus.CANCELLED: set(),
}

EXPENSE_TRANSITIONS: dict[ExpenseStatus, set[ExpenseStatus]] = {
    ExpenseStatus.PENDING: {ExpenseStatus.APPROVED, ExpenseStatus.REJECTED},
    ExpenseStatus.APPROVED: set(),
    ExpenseStatus.REJECTED: set(),
}

LEAVE_TRANSITIONS: dict[LeaveStatus, set[LeaveStatus]] = {
    LeaveStatus.PENDING: {LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.CANCELLED},
    LeaveStatus.APPROVED: set(),
    LeaveStatus.REJECTED: set(),
    LeaveStatus.CANCELLED: set(),
}

MEETING_TRANSITIONS: dict[MeetingStatus, set[MeetingStatus]] = {
    MeetingStatus.SCHEDULED: {MeetingStatus.COMPLETED, MeetingStatus.CANCELLED},
    MeetingStatus.COMPLETED: set(),
    MeetingStatus.CANCELLED: set(),
}

SITE_VISIT_TRANSITIONS: dict[SiteVisitStatus, set[SiteVisitStatus]] = {
    SiteVisitStatus.SCHEDULED: {SiteVisitStatus.COMPLETED, SiteVisitStatus.CANCELLED},
    SiteVisitStatus.COMPLETED: set(),
    SiteVisitStatus.CANCELLED: set(),
}

TIMESHEET_TRANSITIONS: dict[TimesheetStatus, set[TimesheetStatus]] = {
    TimesheetStatus.DRAFT: {TimesheetStatus.SUBMITTED},
    TimesheetStatus.SUBMITTED: {TimesheetStatus.APPROVED, TimesheetStatus.REJECTED},
    # A rejected week returns to the employee for fixes; resubmit re-enters review.
    TimesheetStatus.REJECTED: {TimesheetStatus.SUBMITTED},
    TimesheetStatus.APPROVED: set(),
}

_ERROR_MAP = {
    TaskStatus: TaskError,
    PhaseStatus: ProjectError,
    ProjectStatus: ProjectError,
    ExpenseStatus: FinanceError,
    LeaveStatus: LeaveError,
    MeetingStatus: MeetingError,
    SiteVisitStatus: SiteVisitError,
    TimesheetStatus: TimesheetError,
}


def assert_transition(
    current: TaskStatus
    | PhaseStatus
    | ProjectStatus
    | ExpenseStatus
    | LeaveStatus
    | MeetingStatus
    | SiteVisitStatus
    | TimesheetStatus,
    target: TaskStatus
    | PhaseStatus
    | ProjectStatus
    | ExpenseStatus
    | LeaveStatus
    | MeetingStatus
    | SiteVisitStatus
    | TimesheetStatus,
    model_name: str = "record",
) -> None:
    """Raise if current → target is not a valid transition.

    Each status enum maps to exactly one transition table.
    """
    transitions = {
        TaskStatus: TASK_TRANSITIONS,
        PhaseStatus: PHASE_TRANSITIONS,
        ProjectStatus: PROJECT_TRANSITIONS,
        ExpenseStatus: EXPENSE_TRANSITIONS,
        LeaveStatus: LEAVE_TRANSITIONS,
        MeetingStatus: MEETING_TRANSITIONS,
        SiteVisitStatus: SITE_VISIT_TRANSITIONS,
        TimesheetStatus: TIMESHEET_TRANSITIONS,
    }
    table = transitions.get(type(current))
    if table is None:
        return
    allowed = table.get(current, set())
    if target not in allowed:
        allowed_names = (
            ", ".join(s.value for s in sorted(allowed, key=lambda s: s.value))
            or "(terminal — no transitions)"
        )
        error_cls = _ERROR_MAP.get(type(current), Exception)
        raise error_cls(
            f"Cannot transition {model_name} from '{current.value}' to '{target.value}'. "
            f"Allowed: {allowed_names}",
            409,
        )
