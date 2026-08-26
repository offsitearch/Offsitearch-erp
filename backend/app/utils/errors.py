"""Domain error classes.

All domain errors share the same shape: a message and an HTTP status code.
"""


class DomainError(Exception):
    """Base for all domain-specific errors."""

    def __init__(self, message: str, status_code: int = 409) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthError(DomainError):
    """Raised when authentication/authorization fails."""


class AttendanceError(DomainError):
    """Raised when an attendance operation violates business rules."""


class LeaveError(DomainError):
    """Raised when a leave operation violates business rules."""


class EmployeeError(DomainError):
    """Raised when an HR/employee operation violates business rules."""


class ProjectError(DomainError):
    """Raised when a project operation violates business rules."""


class ClientError(DomainError):
    """Raised when a client/CRM operation violates business rules."""


class TaskError(DomainError):
    """Raised when a task operation violates business rules."""


class FinanceError(DomainError):
    """Raised when a finance operation violates business rules."""


class PayrollError(DomainError):
    """Raised when a payroll operation violates business rules."""


class SettingsError(DomainError):
    """Raised when a settings/admin operation violates business rules."""


class MeetingError(DomainError):
    """Raised when a meeting/scheduling operation violates business rules."""


class SiteVisitError(DomainError):
    """Raised when a site-visit operation violates business rules."""


class TimesheetError(DomainError):
    """Raised when a timesheet operation violates business rules."""
