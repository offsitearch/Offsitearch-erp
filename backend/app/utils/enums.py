from enum import Enum


def _enum_values(enum_class: type[Enum]) -> list[str]:
    """Return lowercase string values for a str Enum, used by SAEnum columns."""
    return [e.value for e in enum_class]


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    HALF_DAY = "half_day"
    WORK_FROM_HOME = "work_from_home"
    ON_LEAVE = "on_leave"


class AttendanceMethod(str, Enum):
    WEB = "web"
    MANUAL = "manual"
    QR = "qr"
    GPS = "gps"
    IP = "ip"


class LeaveType(str, Enum):
    CASUAL = "casual"
    SICK = "sick"
    EARNED = "earned"
    COMPENSATORY = "compensatory"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    WORK_FROM_HOME = "work_from_home"
    UNPAID = "unpaid"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ProjectType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INTERIOR = "interior"
    INSTITUTIONAL = "institutional"
    LANDSCAPE = "landscape"
    URBAN_PLANNING = "urban_planning"
    RENOVATION = "renovation"
    MIXED_USE = "mixed_use"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    CONCEPT = "concept"
    DESIGN = "design"
    UNDER_REVIEW = "under_review"
    IN_CONSTRUCTION = "in_construction"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class PhaseStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


class ClientType(str, Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"
    DEVELOPER = "developer"
    GOVERNMENT = "government"


class CommunicationType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    SITE_VISIT = "site_visit"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    CASH = "cash"
    CHEQUE = "cheque"
    CARD = "card"


class ExpenseStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExpenseCategory(str, Enum):
    TRAVEL = "travel"
    MATERIAL = "material"
    SOFTWARE = "software"
    PRINTING = "printing"
    SUBCONTRACT = "subcontract"
    OFFICE = "office"
    UTILITIES = "utilities"
    SALARY = "salary"
    OTHER = "other"


class PayrollStatus(str, Enum):
    DRAFT = "draft"
    PROCESSED = "processed"


class DealStage(str, Enum):
    LEAD = "lead"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class NoticeImportance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MeetingType(str, Enum):
    INTERNAL = "internal"
    CLIENT = "client"
    SITE = "site"
    VIDEO = "video"


class MeetingStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RsvpStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class SiteVisitStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TimesheetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
