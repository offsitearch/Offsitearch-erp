from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.security import generate_email, generate_numeric_password, hash_password
from app.models import (
    Attendance,
    Client,
    Department,
    Expense,
    Invoice,
    InvoiceItem,
    Leave,
    Meeting,
    MeetingAttendee,
    Notice,
    OrgLevel,
    Project,
    SalaryComponent,
    SiteVisit,
    Task,
    User,
)
from app.utils.enums import (
    AttendanceStatus,
    ExpenseCategory,
    ExpenseStatus,
    InvoiceStatus,
    LeaveStatus,
    LeaveType,
    MeetingStatus,
    MeetingType,
    NoticeImportance,
    RsvpStatus,
    SiteVisitStatus,
    TaskPriority,
    TaskStatus,
)

from app.utils.shared import now_local

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TODAY = now_local().date()

DEMO_USERS = [
    {
        "name": "Priya Mehta",
        "department": "Corporate / Administration",
        "level": "L3",
        "designation": "Studio Manager",
        "phone": "9876543210",
        "gender": "female",
        "date_of_joining": date(2026, 2, 14),
        "skills": ["office-management", "hr-operations", "finance"],
    },
    {
        "name": "Arjun Nair",
        "department": "Project & Site",
        "level": "L3",
        "designation": "Senior Project Lead",
        "phone": "9876543211",
        "gender": "male",
        "date_of_joining": date(2026, 1, 20),
        "skills": ["project-management", "client-coordination", "scheduling"],
    },
    {
        "name": "Sneha Patil",
        "department": "Architecture & Design",
        "level": "L3",
        "designation": "Design Lead",
        "phone": "9876543212",
        "gender": "female",
        "date_of_joining": date(2026, 1, 20),
        "skills": ["conceptual-design", "revit", "team-leadership"],
    },
    {
        "name": "Vikram Desai",
        "department": "Architecture & Design",
        "level": "L4",
        "designation": "Senior Architect",
        "phone": "9876543213",
        "gender": "male",
        "date_of_joining": date(2026, 3, 1),
        "skills": ["architectural-design", "autocad", "site-coordination"],
    },
    {
        "name": "Neha Gupta",
        "department": "Interior Design",
        "level": "L5",
        "designation": "Interior Designer",
        "phone": "9876543214",
        "gender": "female",
        "date_of_joining": date(2026, 3, 15),
        "skills": ["interior-design", "3ds-max", "materials"],
    },
    {
        "name": "Rahul Sharma",
        "department": "BIM & Visualization",
        "level": "L5",
        "designation": "BIM Coordinator",
        "phone": "9876543215",
        "gender": "male",
        "date_of_joining": date(2026, 4, 1),
        "skills": ["bim", "revit", "navisworks"],
    },
    {
        "name": "Amit Joshi",
        "department": "BIM & Visualization",
        "level": "L5",
        "designation": "3D Artist",
        "phone": "9876543216",
        "gender": "male",
        "date_of_joining": date(2026, 4, 10),
        "skills": ["3ds-max", "vray", "lumion"],
    },
    {
        "name": "Kavita Reddy",
        "department": "Project & Site",
        "level": "L5",
        "designation": "Project Coordinator",
        "phone": "9876543217",
        "gender": "female",
        "date_of_joining": date(2026, 2, 28),
        "skills": ["scheduling", "documentation", "ms-project"],
    },
    {
        "name": "Sanjay Kumar",
        "department": "Project & Site",
        "level": "L5",
        "designation": "Site Engineer",
        "phone": "9876543218",
        "gender": "male",
        "date_of_joining": date(2026, 3, 10),
        "skills": ["site-supervision", "quality-control", "safety"],
    },
    {
        "name": "Pooja Singh",
        "department": "Business & Operations",
        "level": "L3",
        "designation": "BD Manager",
        "phone": "9876543219",
        "gender": "female",
        "date_of_joining": date(2026, 2, 15),
        "skills": ["business-development", "client-relations", "marketing"],
    },
    {
        "name": "Ravi Verma",
        "department": "Architecture & Design",
        "level": "L6",
        "designation": "Design Intern",
        "phone": "9876543220",
        "gender": "male",
        "date_of_joining": date(2026, 5, 1),
        "skills": ["autocad", "sketchup", "hand-drafting"],
    },
    {
        "name": "Deepa Iyer",
        "department": "BIM & Visualization",
        "level": "L6",
        "designation": "Rendering Intern",
        "phone": "9876543221",
        "gender": "female",
        "date_of_joining": date(2026, 5, 15),
        "skills": ["lumion", "photoshop", "enscape"],
    },
]

SALARY_DATA = {
    "Priya Mehta": 2400000,
    "Arjun Nair": 1800000,
    "Sneha Patil": 1800000,
    "Vikram Desai": 1200000,
    "Neha Gupta": 900000,
    "Rahul Sharma": 1000000,
    "Amit Joshi": 900000,
    "Kavita Reddy": 800000,
    "Sanjay Kumar": 900000,
    "Pooja Singh": 900000,
}

REPORTING_MAP = {
    "Vikram Desai": "Sneha Patil",
    "Neha Gupta": "Sneha Patil",
    "Ravi Verma": "Sneha Patil",
    "Rahul Sharma": "Arjun Nair",
    "Amit Joshi": "Sneha Patil",
    "Kavita Reddy": "Arjun Nair",
    "Sanjay Kumar": "Arjun Nair",
    "Deepa Iyer": "Sneha Patil",
    "Pooja Singh": "Priya Mehta",
}

TASK_DATA = [
    {
        "title": "Prepare schematic design for Sharma Residence",
        "description": "Develop initial schematic design options for the villa project including massing studies and spatial planning",
        "project": "Sharma Residence - Villa",
        "assigned_to": "Vikram Desai",
        "assigned_by": "Sneha Patil",
        "priority": TaskPriority.HIGH,
        "status": TaskStatus.IN_PROGRESS,
        "start_date": TODAY - timedelta(days=30),
        "due_date": TODAY + timedelta(days=15),
        "estimated_hours": Decimal("40.00"),
        "tags": ["design", "residential"],
    },
    {
        "title": "Structural BIM coordination - Skyline Tower",
        "description": "Coordinate structural BIM model with MEP consultants for Tower B floors G-5",
        "project": "Skyline Commercial Tower B",
        "assigned_to": "Rahul Sharma",
        "assigned_by": "Arjun Nair",
        "priority": TaskPriority.URGENT,
        "status": TaskStatus.IN_PROGRESS,
        "start_date": TODAY - timedelta(days=20),
        "due_date": TODAY + timedelta(days=5),
        "estimated_hours": Decimal("60.00"),
        "tags": ["bim", "structural", "commercial"],
    },
    {
        "title": "Interior concept mood boards - Kaveri Gallery",
        "description": "Create mood boards for gallery and cafe interior zones including material palettes",
        "project": "Kaveri Gallery Interiors",
        "assigned_to": "Neha Gupta",
        "assigned_by": "Sneha Patil",
        "priority": TaskPriority.MEDIUM,
        "status": TaskStatus.REVIEW,
        "start_date": TODAY - timedelta(days=14),
        "due_date": TODAY + timedelta(days=3),
        "estimated_hours": Decimal("20.00"),
        "tags": ["concept", "interior"],
    },
    {
        "title": "3D exterior render - Sharma Residence front elevation",
        "description": "Produce photorealistic exterior render of front elevation with landscaping context",
        "project": "Sharma Residence - Villa",
        "assigned_to": "Amit Joshi",
        "assigned_by": "Sneha Patil",
        "priority": TaskPriority.HIGH,
        "status": TaskStatus.TODO,
        "start_date": TODAY + timedelta(days=2),
        "due_date": TODAY + timedelta(days=12),
        "estimated_hours": Decimal("24.00"),
        "tags": ["rendering", "residential"],
    },
    {
        "title": "Construction drawing set - Sharma ground floor",
        "description": "Prepare complete CD set for ground floor including plans, sections, and details",
        "project": "Sharma Residence - Villa",
        "assigned_to": "Rahul Sharma",
        "assigned_by": "Arjun Nair",
        "priority": TaskPriority.HIGH,
        "status": TaskStatus.IN_PROGRESS,
        "start_date": TODAY - timedelta(days=25),
        "due_date": TODAY + timedelta(days=20),
        "estimated_hours": Decimal("80.00"),
        "tags": ["construction-drawing", "residential"],
    },
    {
        "title": "Site survey report compilation",
        "description": "Compile site survey data and measurements for Sharma Residence site",
        "project": "Sharma Residence - Villa",
        "assigned_to": "Sanjay Kumar",
        "assigned_by": "Arjun Nair",
        "priority": TaskPriority.MEDIUM,
        "status": TaskStatus.DONE,
        "start_date": TODAY - timedelta(days=35),
        "due_date": TODAY - timedelta(days=25),
        "estimated_hours": Decimal("12.00"),
        "actual_hours": Decimal("14.00"),
        "tags": ["survey", "site"],
    },
    {
        "title": "MEP coordination drawings - Skyline Tower",
        "description": "Prepare MEP coordination drawings integrating mechanical, electrical and plumbing services",
        "project": "Skyline Commercial Tower B",
        "assigned_to": "Rahul Sharma",
        "assigned_by": "Arjun Nair",
        "priority": TaskPriority.URGENT,
        "status": TaskStatus.REVIEW,
        "start_date": TODAY - timedelta(days=18),
        "due_date": TODAY + timedelta(days=2),
        "estimated_hours": Decimal("50.00"),
        "tags": ["mep", "coordination", "commercial"],
    },
    {
        "title": "Client presentation - Kaveri Gallery concept",
        "description": "Prepare presentation deck for client meeting showcasing concept design options",
        "project": "Kaveri Gallery Interiors",
        "assigned_to": "Neha Gupta",
        "assigned_by": "Sneha Patil",
        "priority": TaskPriority.HIGH,
        "status": TaskStatus.DONE,
        "start_date": TODAY - timedelta(days=10),
        "due_date": TODAY - timedelta(days=3),
        "estimated_hours": Decimal("16.00"),
        "actual_hours": Decimal("18.00"),
        "tags": ["presentation", "interior"],
    },
    {
        "title": "Furniture layout plan - Kaveri Gallery cafe",
        "description": "Develop detailed furniture layout for the cafe area with seating arrangements",
        "project": "Kaveri Gallery Interiors",
        "assigned_to": "Neha Gupta",
        "assigned_by": "Sneha Patil",
        "priority": TaskPriority.MEDIUM,
        "status": TaskStatus.IN_PROGRESS,
        "start_date": TODAY - timedelta(days=8),
        "due_date": TODAY + timedelta(days=7),
        "estimated_hours": Decimal("18.00"),
        "tags": ["furniture", "interior"],
    },
    {
        "title": "Landscape design - Sharma Residence garden",
        "description": "Develop landscape design for front and rear garden areas with planting scheme",
        "project": "Sharma Residence - Villa",
        "assigned_to": "Vikram Desai",
        "assigned_by": "Sneha Patil",
        "priority": TaskPriority.LOW,
        "status": TaskStatus.TODO,
        "start_date": TODAY + timedelta(days=10),
        "due_date": TODAY + timedelta(days=30),
        "estimated_hours": Decimal("24.00"),
        "tags": ["landscape", "residential"],
    },
    {
        "title": "Facade design options - Skyline Tower",
        "description": "Develop 3 facade design options for client review including material and glazing specifications",
        "project": "Skyline Commercial Tower B",
        "assigned_to": "Vikram Desai",
        "assigned_by": "Sneha Patil",
        "priority": TaskPriority.HIGH,
        "status": TaskStatus.REVIEW,
        "start_date": TODAY - timedelta(days=22),
        "due_date": TODAY + timedelta(days=4),
        "estimated_hours": Decimal("36.00"),
        "tags": ["facade", "commercial"],
    },
    {
        "title": "Quantity estimation - Kaveri Gallery materials",
        "description": "Prepare material quantity estimation for interior finishes and fixtures",
        "project": "Kaveri Gallery Interiors",
        "assigned_to": "Kavita Reddy",
        "assigned_by": "Arjun Nair",
        "priority": TaskPriority.MEDIUM,
        "status": TaskStatus.TODO,
        "start_date": TODAY + timedelta(days=5),
        "due_date": TODAY + timedelta(days=15),
        "estimated_hours": Decimal("14.00"),
        "tags": ["estimation", "interior"],
    },
    {
        "title": "3D walkthrough - Sharma Residence interior",
        "description": "Create animated 3D walkthrough of villa interior spaces",
        "project": "Sharma Residence - Villa",
        "assigned_to": "Amit Joshi",
        "assigned_by": "Sneha Patil",
        "priority": TaskPriority.MEDIUM,
        "status": TaskStatus.TODO,
        "start_date": TODAY + timedelta(days=5),
        "due_date": TODAY + timedelta(days=20),
        "estimated_hours": Decimal("40.00"),
        "tags": ["walkthrough", "residential"],
    },
    {
        "title": "Site progress documentation",
        "description": "Document current construction progress at Sharma Residence site with photos and notes",
        "project": "Sharma Residence - Villa",
        "assigned_to": "Sanjay Kumar",
        "assigned_by": "Arjun Nair",
        "priority": TaskPriority.LOW,
        "status": TaskStatus.DONE,
        "start_date": TODAY - timedelta(days=7),
        "due_date": TODAY - timedelta(days=1),
        "estimated_hours": Decimal("6.00"),
        "actual_hours": Decimal("5.00"),
        "tags": ["documentation", "site"],
    },
    {
        "title": "Fire safety compliance review - Skyline Tower",
        "description": "Review fire safety compliance for Tower B against NBC and local regulations",
        "project": "Skyline Commercial Tower B",
        "assigned_to": "Arjun Nair",
        "assigned_by": "Arjun Nair",
        "priority": TaskPriority.URGENT,
        "status": TaskStatus.IN_PROGRESS,
        "start_date": TODAY - timedelta(days=5),
        "due_date": TODAY + timedelta(days=8),
        "estimated_hours": Decimal("20.00"),
        "tags": ["compliance", "commercial", "fire-safety"],
    },
]

EXPENSE_DATA = [
    {
        "description": "Site visit cab fare to Kothrud",
        "category": ExpenseCategory.TRAVEL,
        "amount": Decimal("850.00"),
        "expense_date": TODAY - timedelta(days=20),
        "project": "Sharma Residence - Villa",
        "paid_by": "Sanjay Kumar",
        "status": ExpenseStatus.APPROVED,
    },
    {
        "description": "Material sample procurement - marble tiles",
        "category": ExpenseCategory.MATERIAL,
        "amount": Decimal("12500.00"),
        "expense_date": TODAY - timedelta(days=15),
        "project": "Kaveri Gallery Interiors",
        "paid_by": "Neha Gupta",
        "status": ExpenseStatus.APPROVED,
    },
    {
        "description": "AutoCAD annual subscription renewal",
        "category": ExpenseCategory.SOFTWARE,
        "amount": Decimal("45000.00"),
        "expense_date": TODAY - timedelta(days=10),
        "project": None,
        "paid_by": "Priya Mehta",
        "status": ExpenseStatus.APPROVED,
    },
    {
        "description": "New mouse and keyboard for workstation",
        "category": ExpenseCategory.OFFICE,
        "amount": Decimal("3200.00"),
        "expense_date": TODAY - timedelta(days=8),
        "project": None,
        "paid_by": "Amit Joshi",
        "status": ExpenseStatus.PENDING,
    },
    {
        "description": "Printed presentation boards for client meeting",
        "category": ExpenseCategory.PRINTING,
        "amount": Decimal("6800.00"),
        "expense_date": TODAY - timedelta(days=5),
        "project": "Kaveri Gallery Interiors",
        "paid_by": "Neha Gupta",
        "status": ExpenseStatus.PENDING,
    },
    {
        "description": "Team lunch for project milestone celebration",
        "category": ExpenseCategory.OTHER,
        "amount": Decimal("4500.00"),
        "expense_date": TODAY - timedelta(days=3),
        "project": "Sharma Residence - Villa",
        "paid_by": "Arjun Nair",
        "status": ExpenseStatus.APPROVED,
    },
    {
        "description": "V-Ray license upgrade for rendering workstation",
        "category": ExpenseCategory.SOFTWARE,
        "amount": Decimal("28000.00"),
        "expense_date": TODAY - timedelta(days=2),
        "project": None,
        "paid_by": "Amit Joshi",
        "status": ExpenseStatus.PENDING,
    },
    {
        "description": "Survey equipment rental - total station",
        "category": ExpenseCategory.OTHER,
        "amount": Decimal("8500.00"),
        "expense_date": TODAY - timedelta(days=12),
        "project": "Sharma Residence - Villa",
        "paid_by": "Sanjay Kumar",
        "status": ExpenseStatus.APPROVED,
    },
    {
        "description": "Model making material - foam board and glue",
        "category": ExpenseCategory.MATERIAL,
        "amount": Decimal("2200.00"),
        "expense_date": TODAY - timedelta(days=7),
        "project": "Skyline Commercial Tower B",
        "paid_by": "Vikram Desai",
        "status": ExpenseStatus.REJECTED,
    },
    {
        "description": "Client dinner entertainment expenses",
        "category": ExpenseCategory.OTHER,
        "amount": Decimal("15000.00"),
        "expense_date": TODAY - timedelta(days=1),
        "project": "Skyline Commercial Tower B",
        "paid_by": "Pooja Singh",
        "status": ExpenseStatus.PENDING,
    },
]

INVOICE_DATA = [
    {
        "invoice_number": "INV-2026-001",
        "client": "Meera & Rajesh Sharma",
        "project": "Sharma Residence - Villa",
        "invoice_date": TODAY - timedelta(days=45),
        "due_date": TODAY - timedelta(days=15),
        "items": [
            {
                "description": "Schematic Design Phase",
                "quantity": Decimal("1"),
                "rate": Decimal("393750.00"),
            },
            {
                "description": "Design Development Phase",
                "quantity": Decimal("1"),
                "rate": Decimal("393750.00"),
            },
        ],
        "status": InvoiceStatus.PAID,
        "paid_amount": Decimal("787500.00"),
        "payment_date": TODAY - timedelta(days=10),
    },
    {
        "invoice_number": "INV-2026-002",
        "client": "Skyline Developers",
        "project": "Skyline Commercial Tower B",
        "invoice_date": TODAY - timedelta(days=30),
        "due_date": TODAY + timedelta(days=30),
        "items": [
            {
                "description": "Concept Design Fee",
                "quantity": Decimal("1"),
                "rate": Decimal("2175000.00"),
            },
            {
                "description": "3D Visualization Package",
                "quantity": Decimal("1"),
                "rate": Decimal("870000.00"),
            },
            {
                "description": "BIM Modelling Services",
                "quantity": Decimal("1"),
                "rate": Decimal("1305000.00"),
            },
        ],
        "status": InvoiceStatus.SENT,
        "paid_amount": Decimal("0"),
    },
    {
        "invoice_number": "INV-2026-003",
        "client": "Kaveri Art Gallery",
        "project": "Kaveri Gallery Interiors",
        "invoice_date": TODAY - timedelta(days=60),
        "due_date": TODAY - timedelta(days=30),
        "items": [
            {
                "description": "Interior Concept Design",
                "quantity": Decimal("1"),
                "rate": Decimal("220500.00"),
            },
            {
                "description": "Detailed Design & Drawings",
                "quantity": Decimal("1"),
                "rate": Decimal("220500.00"),
            },
        ],
        "status": InvoiceStatus.PAID,
        "paid_amount": Decimal("441000.00"),
        "payment_date": TODAY - timedelta(days=25),
    },
    {
        "invoice_number": "INV-2026-004",
        "client": "Meera & Rajesh Sharma",
        "project": "Sharma Residence - Villa",
        "invoice_date": TODAY - timedelta(days=15),
        "due_date": TODAY + timedelta(days=15),
        "items": [
            {
                "description": "Construction Drawings Phase",
                "quantity": Decimal("1"),
                "rate": Decimal("393750.00"),
            },
        ],
        "status": InvoiceStatus.PARTIAL,
        "paid_amount": Decimal("196875.00"),
    },
    {
        "invoice_number": "INV-2026-005",
        "client": "Skyline Developers",
        "project": "Skyline Commercial Tower B",
        "invoice_date": TODAY - timedelta(days=5),
        "due_date": TODAY + timedelta(days=55),
        "items": [
            {
                "description": "Schematic Design Phase",
                "quantity": Decimal("1"),
                "rate": Decimal("2175000.00"),
            },
            {
                "description": "MEP Coordination Services",
                "quantity": Decimal("1"),
                "rate": Decimal("1087500.00"),
            },
        ],
        "status": InvoiceStatus.DRAFT,
        "paid_amount": Decimal("0"),
    },
]

MEETING_DATA = [
    {
        "title": "Weekly Design Review - Sharma Residence",
        "description": "Review design progress and discuss client feedback on schematic options",
        "meeting_type": MeetingType.INTERNAL,
        "scheduled_at": now_local() - timedelta(days=5, hours=2),
        "duration_minutes": 60,
        "location": "Studio Conference Room",
        "status": MeetingStatus.COMPLETED,
        "organizer": "Sneha Patil",
        "attendees": ["Vikram Desai", "Neha Gupta", "Amit Joshi"],
    },
    {
        "title": "Client Presentation - Kaveri Gallery Concept",
        "description": "Present concept design options to client with mood boards and 3D previews",
        "meeting_type": MeetingType.CLIENT,
        "scheduled_at": now_local() - timedelta(days=3, hours=3),
        "duration_minutes": 90,
        "location": "Kaveri Arts Gallery, Koregaon Park",
        "status": MeetingStatus.COMPLETED,
        "organizer": "Sneha Patil",
        "attendees": ["Neha Gupta", "Pooja Singh"],
    },
    {
        "title": "Site Coordination - Sharma Residence",
        "description": "Discuss construction progress and resolve on-site issues with contractor",
        "meeting_type": MeetingType.SITE,
        "scheduled_at": now_local() - timedelta(days=1, hours=2),
        "duration_minutes": 120,
        "location": "Sharma Residence Site, Kothrud",
        "status": MeetingStatus.COMPLETED,
        "organizer": "Arjun Nair",
        "attendees": ["Sanjay Kumar", "Rahul Sharma"],
    },
    {
        "title": "Skyline Tower B - Project Kickoff",
        "description": "Kickoff meeting with Skyline team to discuss project scope, timeline, and deliverables",
        "meeting_type": MeetingType.CLIENT,
        "scheduled_at": now_local() + timedelta(days=2, hours=1),
        "duration_minutes": 120,
        "location": "Skyline Developers Office, Baner",
        "status": MeetingStatus.SCHEDULED,
        "organizer": "Arjun Nair",
        "attendees": ["Sneha Patil", "Rahul Sharma", "Pooja Singh"],
    },
    {
        "title": "Monthly All-Hands Studio Meeting",
        "description": "Studio-wide meeting to discuss company updates, project pipeline, and team announcements",
        "meeting_type": MeetingType.INTERNAL,
        "scheduled_at": now_local() + timedelta(days=5, hours=0),
        "duration_minutes": 60,
        "location": "Studio Main Hall",
        "status": MeetingStatus.SCHEDULED,
        "organizer": "Priya Mehta",
        "attendees": [
            "Arjun Nair",
            "Sneha Patil",
            "Vikram Desai",
            "Neha Gupta",
            "Rahul Sharma",
        ],
    },
]

NOTICE_DATA = [
    {
        "title": "Office Timings Updated for Monsoon Season",
        "body": "Effective from July 1, the office will operate from 9:30 AM to 6:30 PM during monsoon months (July-September) to accommodate adjusted commute times. Please plan your schedules accordingly.",
        "importance": NoticeImportance.HIGH,
        "is_pinned": True,
        "publish_date": TODAY - timedelta(days=5),
        "expiry_date": TODAY + timedelta(days=90),
    },
    {
        "title": "Team Outing Planned for August",
        "body": "We are organizing a team outing to Lonavala on August 22 (Saturday). Activities include trekking, lunch at a resort, and team-building exercises. Please confirm your attendance by August 10.",
        "importance": NoticeImportance.MEDIUM,
        "is_pinned": False,
        "publish_date": TODAY - timedelta(days=2),
        "expiry_date": TODAY + timedelta(days=30),
    },
    {
        "title": "New BIM Software Training Sessions",
        "body": "Revit advanced training sessions will be conducted every Wednesday from 4:00 PM to 5:30 PM for the next 4 weeks. Attendance is mandatory for all design and technical team members.",
        "importance": NoticeImportance.MEDIUM,
        "is_pinned": True,
        "publish_date": TODAY - timedelta(days=1),
        "expiry_date": TODAY + timedelta(days=28),
    },
]

LEAVE_DATA = [
    {
        "user": "Neha Gupta",
        "leave_type": LeaveType.CASUAL,
        "from_date": TODAY - timedelta(days=10),
        "to_date": TODAY - timedelta(days=9),
        "total_days": 2.0,
        "reason": "Family function out of town",
        "status": LeaveStatus.APPROVED,
        "approved_by": "Priya Mehta",
    },
    {
        "user": "Rahul Sharma",
        "leave_type": LeaveType.SICK,
        "from_date": TODAY - timedelta(days=5),
        "to_date": TODAY - timedelta(days=5),
        "total_days": 1.0,
        "reason": "Not feeling well, doctor appointment",
        "status": LeaveStatus.APPROVED,
        "approved_by": "Arjun Nair",
    },
    {
        "user": "Sanjay Kumar",
        "leave_type": LeaveType.EARNED,
        "from_date": TODAY + timedelta(days=7),
        "to_date": TODAY + timedelta(days=9),
        "total_days": 3.0,
        "reason": "Family vacation to Kerala",
        "status": LeaveStatus.PENDING,
        "approved_by": None,
    },
    {
        "user": "Amit Joshi",
        "leave_type": LeaveType.WORK_FROM_HOME,
        "from_date": TODAY + timedelta(days=1),
        "to_date": TODAY + timedelta(days=1),
        "total_days": 1.0,
        "reason": "Home renovation work, will be available online",
        "status": LeaveStatus.APPROVED,
        "approved_by": "Sneha Patil",
    },
    {
        "user": "Pooja Singh",
        "leave_type": LeaveType.CASUAL,
        "from_date": TODAY + timedelta(days=14),
        "to_date": TODAY + timedelta(days=14),
        "total_days": 1.0,
        "reason": "Personal appointment",
        "status": LeaveStatus.REJECTED,
        "approved_by": "Priya Mehta",
    },
]

SITE_VISIT_DATA = [
    {
        "project": "Sharma Residence - Villa",
        "visit_date": TODAY - timedelta(days=14),
        "start_time": time(10, 0),
        "end_time": time(12, 30),
        "status": SiteVisitStatus.COMPLETED,
        "purpose": "Foundation inspection and structural review",
        "notes": "Foundation pour completed. Rebar placement reviewed. Minor alignment correction needed at grid line C-3. Next visit scheduled for slab casting.",
        "location": "Sharma Residence Site, Kothrud, Pune",
        "weather": "Sunny, 32Â°C",
        "created_by": "Arjun Nair",
    },
    {
        "project": "Sharma Residence - Villa",
        "visit_date": TODAY - timedelta(days=5),
        "start_time": time(9, 30),
        "end_time": time(11, 0),
        "status": SiteVisitStatus.COMPLETED,
        "purpose": "Plumbing rough-in review",
        "notes": "Reviewed plumbing layout on ground floor. Two minor changes recommended for kitchen drainage routing. Contractor agreed to implement before next pour.",
        "location": "Sharma Residence Site, Kothrud, Pune",
        "weather": "Overcast, 28Â°C",
        "created_by": "Sanjay Kumar",
    },
    {
        "project": "Sharma Residence - Villa",
        "visit_date": TODAY + timedelta(days=3),
        "start_time": time(10, 0),
        "end_time": time(12, 0),
        "status": SiteVisitStatus.SCHEDULED,
        "purpose": "First floor slab casting supervision",
        "notes": "Supervise slab casting for first floor. Ensure electrical conduit placement matches drawing. Concrete mix design to be verified on-site.",
        "location": "Sharma Residence Site, Kothrud, Pune",
        "weather": None,
        "created_by": "Arjun Nair",
    },
]

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def seed_demo(db) -> None:
    """Create demo / staging data. Only called when SEED_DEMO=true."""
    await _seed_users(db)
    await _seed_salary_components(db)
    await _seed_tasks(db)
    await _seed_expenses(db)
    await _seed_invoices(db)
    await _seed_meetings(db)
    await _seed_notices(db)
    await _seed_leaves(db)
    await _seed_attendance(db)
    await _seed_site_visits(db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_users(db) -> None:
    """Create demo users with reporting relationships."""
    from app.core.security import format_login_id

    existing_emails = set()
    cohort_seq: dict[int, int] = {}
    for u_data in DEMO_USERS:
        email = generate_email(u_data["name"], u_data["date_of_joining"])
        exists = await db.execute(select(User).where(User.email == email))
        if exists.scalar_one_or_none():
            existing_emails.add(email)
            continue
        password = generate_numeric_password()

        dept_id = (
            await db.execute(select(Department.id).where(Department.name == u_data["department"]))
        ).scalar_one_or_none()

        level_id = None
        if u_data.get("level"):
            level_id = (
                await db.execute(select(OrgLevel.id).where(OrgLevel.code == u_data["level"]))
            ).scalar_one_or_none()

        joining = u_data.get("date_of_joining")
        year = joining.year if joining else now_local().date().year
        while True:
            seq = cohort_seq.get(year, 0) + 1
            cohort_seq[year] = seq
            login_id = format_login_id(year, seq)
            taken = await db.execute(select(User).where(User.login_id == login_id))
            if taken.scalar_one_or_none() is None:
                break

        user = User(
            email=email,
            login_id=login_id,
            name=u_data["name"],
            designation=u_data["designation"],
            phone=u_data["phone"],
            gender=u_data["gender"],
            date_of_joining=u_data["date_of_joining"],
            skills=u_data["skills"],
            department_id=dept_id,
            org_level_id=level_id,
            password_hash=hash_password(password),
        )
        db.add(user)
        existing_emails.add(email)
    await db.flush()

    for user_name, manager_name in REPORTING_MAP.items():
        user_email = None
        manager_email = None
        for u_data in DEMO_USERS:
            if u_data["name"] == user_name:
                user_email = generate_email(user_name, u_data["date_of_joining"])
            if u_data["name"] == manager_name:
                manager_email = generate_email(manager_name, u_data["date_of_joining"])

        if user_email and manager_email:
            user = (
                await db.execute(select(User).where(User.email == user_email))
            ).scalar_one_or_none()
            manager = (
                await db.execute(select(User).where(User.email == manager_email))
            ).scalar_one_or_none()
            if user and manager and user.reporting_to_id is None:
                user.reporting_to_id = manager.id
    await db.commit()


async def _seed_salary_components(db) -> None:
    """Create salary components for non-intern demo users."""
    for user_name, ctc in SALARY_DATA.items():
        user_data = next(u for u in DEMO_USERS if u["name"] == user_name)
        email = generate_email(user_name, user_data["date_of_joining"])
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            continue

        exists = await db.execute(select(SalaryComponent).where(SalaryComponent.user_id == user.id))
        if exists.scalar_one_or_none():
            continue

        basic = ctc * Decimal("0.40")
        hra = ctc * Decimal("0.20")
        pf = basic * Decimal("0.12")
        special_allowance = ctc - basic - hra - pf

        db.add(
            SalaryComponent(
                user_id=user.id,
                ctc_annual=ctc,
                basic=basic,
                hra=hra,
                special_allowance=special_allowance,
                pf_deduction=pf,
                bank_name="HDFC Bank",
                account_number=f"50100{''.join(str(ord(c)) for c in user_name[:4])}00",
                ifsc_code="HDFC0001234",
                effective_from=user_data["date_of_joining"],
            )
        )
    await db.commit()


async def _seed_tasks(db) -> None:
    """Create demo tasks across projects."""
    projects = {}
    for row in (await db.execute(select(Project))).scalars().all():
        projects[row.name] = row.id

    users = {}
    for row in (await db.execute(select(User))).scalars().all():
        users[row.name] = row.id

    for t in TASK_DATA:
        exists = await db.execute(select(Task).where(Task.title == t["title"]))
        if exists.scalar_one_or_none():
            continue

        db.add(
            Task(
                title=t["title"],
                description=t.get("description"),
                project_id=projects.get(t["project"]),
                assigned_to=users.get(t["assigned_to"]),
                assigned_by=users.get(t["assigned_by"]),
                priority=t["priority"],
                status=t["status"],
                start_date=t.get("start_date"),
                due_date=t.get("due_date"),
                estimated_hours=t.get("estimated_hours"),
                actual_hours=t.get("actual_hours"),
                tags=t.get("tags"),
            )
        )
    await db.commit()


async def _seed_expenses(db) -> None:
    """Create demo expenses with various statuses."""
    projects = {}
    for row in (await db.execute(select(Project))).scalars().all():
        projects[row.name] = row.id

    for e in EXPENSE_DATA:
        desc = e["description"]
        amt = e["amount"]
        exists = await db.execute(
            select(Expense).where(Expense.description == desc, Expense.amount == amt)
        )
        if exists.scalar_one_or_none():
            continue

        db.add(
            Expense(
                category=e["category"],
                description=desc,
                amount=amt,
                expense_date=e["expense_date"],
                project_id=projects.get(e.get("project")) if e.get("project") else None,
                paid_by=e["paid_by"],
                status=e["status"],
            )
        )
    await db.commit()


async def _seed_invoices(db) -> None:
    """Create demo invoices with line items."""
    clients = {}
    for row in (await db.execute(select(Client))).scalars().all():
        clients[row.name] = row.id

    projects = {}
    for row in (await db.execute(select(Project))).scalars().all():
        projects[row.name] = row.id

    for inv in INVOICE_DATA:
        exists = await db.execute(
            select(Invoice).where(Invoice.invoice_number == inv["invoice_number"])
        )
        if exists.scalar_one_or_none():
            continue

        subtotal = sum(item["quantity"] * item["rate"] for item in inv["items"])
        tax_pct = Decimal("18.00")
        tax_amount = (subtotal * tax_pct / Decimal("100")).quantize(Decimal("0.01"))
        total = subtotal + tax_amount

        invoice = Invoice(
            invoice_number=inv["invoice_number"],
            client_id=clients.get(inv["client"]),
            project_id=projects.get(inv.get("project")) if inv.get("project") else None,
            invoice_date=inv["invoice_date"],
            due_date=inv["due_date"],
            subtotal=subtotal,
            tax_percent=tax_pct,
            tax_amount=tax_amount,
            total=total,
            status=inv["status"],
            paid_amount=inv.get("paid_amount", Decimal("0")),
            payment_date=inv.get("payment_date"),
        )
        db.add(invoice)
        await db.flush()

        for item in inv["items"]:
            item_amount = item["quantity"] * item["rate"]
            db.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    description=item["description"],
                    quantity=item["quantity"],
                    rate=item["rate"],
                    amount=item_amount,
                )
            )
    await db.commit()


async def _seed_meetings(db) -> None:
    """Create demo meetings with attendees."""
    users = {}
    for row in (await db.execute(select(User))).scalars().all():
        users[row.name] = row.id

    for m in MEETING_DATA:
        exists = await db.execute(select(Meeting).where(Meeting.title == m["title"]))
        if exists.scalar_one_or_none():
            continue

        meeting = Meeting(
            title=m["title"],
            description=m.get("description"),
            meeting_type=m["meeting_type"],
            scheduled_at=m["scheduled_at"],
            duration_minutes=m["duration_minutes"],
            location=m.get("location"),
            status=m["status"],
            organizer_id=users.get(m["organizer"]),
        )
        db.add(meeting)
        await db.flush()

        for attendee_name in m.get("attendees", []):
            attendee_id = users.get(attendee_name)
            if attendee_id:
                db.add(
                    MeetingAttendee(
                        meeting_id=meeting.id,
                        user_id=attendee_id,
                        rsvp_status=(
                            RsvpStatus.ACCEPTED
                            if m["status"] == MeetingStatus.COMPLETED
                            else RsvpStatus.PENDING
                        ),
                    )
                )
    await db.commit()


async def _seed_notices(db) -> None:
    """Create demo notices."""
    admin = (
        await db.execute(
            select(User).where(
                User.email == generate_email("Priya Mehta", DEMO_USERS[0]["date_of_joining"])
            )
        )
    ).scalar_one_or_none()

    for n in NOTICE_DATA:
        exists = await db.execute(select(Notice).where(Notice.title == n["title"]))
        if exists.scalar_one_or_none():
            continue

        db.add(
            Notice(
                title=n["title"],
                body=n["body"],
                importance=n["importance"],
                is_pinned=n["is_pinned"],
                publish_date=n["publish_date"],
                expiry_date=n["expiry_date"],
                created_by=admin.id if admin else None,
            )
        )
    await db.commit()


async def _seed_leaves(db) -> None:
    """Create demo leave requests with various statuses."""
    users = {}
    for row in (await db.execute(select(User))).scalars().all():
        users[row.name] = row.id

    for entry in LEAVE_DATA:
        user_id = users.get(entry["user"])
        if not user_id:
            continue

        exists = await db.execute(
            select(Leave).where(
                Leave.user_id == user_id,
                Leave.from_date == entry["from_date"],
                Leave.to_date == entry["to_date"],
            )
        )
        if exists.scalar_one_or_none():
            continue

        approver_id = users.get(entry["approved_by"]) if entry.get("approved_by") else None

        db.add(
            Leave(
                user_id=user_id,
                leave_type=entry["leave_type"],
                from_date=entry["from_date"],
                to_date=entry["to_date"],
                total_days=entry["total_days"],
                reason=entry["reason"],
                status=entry["status"],
                approved_by=approver_id,
            )
        )
    await db.commit()


async def _seed_attendance(db) -> None:
    """Create two weeks of attendance records for all demo users."""
    users_result = (
        (
            await db.execute(
                select(User).where(
                    User.date_of_joining.isnot(None),
                    User.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )

    today = now_local().date()
    start_date = today - timedelta(days=14)

    all_records = []
    for user in users_result:
        user_join = user.date_of_joining or start_date
        current = max(start_date, user_join)
        while current <= today:
            if current.weekday() < 5:
                hour = 8
                minute = 45 + (hash(f"{user.id}{current}") % 30)
                check_in = datetime.combine(current, time(hour, minute, 0))

                is_late = check_in.time() > time(9, 15)
                status = AttendanceStatus.LATE if is_late else AttendanceStatus.PRESENT

                check_out = datetime.combine(
                    current, time(17, 45 + (hash(f"{user.id}{current}out") % 30), 0)
                )
                total_hours = Decimal(str(round((check_out - check_in).total_seconds() / 3600, 2)))

                all_records.append(
                    {
                        "user_id": user.id,
                        "date": current,
                        "check_in_time": check_in,
                        "check_out_time": check_out,
                        "status": status,
                        "late_minutes": max(0, (check_in.hour * 60 + check_in.minute) - 555),
                        "total_hours": total_hours,
                    }
                )
            current += timedelta(days=1)

    inserted = 0
    for rec in all_records:
        exists = await db.execute(
            select(Attendance).where(
                Attendance.user_id == rec["user_id"],
                Attendance.date == rec["date"],
            )
        )
        if exists.scalar_one_or_none():
            continue
        db.add(
            Attendance(
                user_id=rec["user_id"],
                date=rec["date"],
                check_in_time=rec["check_in_time"],
                check_out_time=rec["check_out_time"],
                status=rec["status"],
                late_minutes=rec["late_minutes"],
                total_hours=rec["total_hours"],
            )
        )
        inserted += 1
    await db.commit()


async def _seed_site_visits(db) -> None:
    """Create demo site visits for the residential project."""
    projects = {}
    for row in (await db.execute(select(Project))).scalars().all():
        projects[row.name] = row.id

    users = {}
    for row in (await db.execute(select(User))).scalars().all():
        users[row.name] = row.id

    for sv in SITE_VISIT_DATA:
        exists = await db.execute(
            select(SiteVisit).where(
                SiteVisit.project_id == projects.get(sv["project"]),
                SiteVisit.visit_date == sv["visit_date"],
            )
        )
        if exists.scalar_one_or_none():
            continue

        db.add(
            SiteVisit(
                project_id=projects.get(sv["project"]),
                visit_date=sv["visit_date"],
                start_time=sv["start_time"],
                end_time=sv["end_time"],
                status=sv["status"],
                purpose=sv["purpose"],
                notes=sv["notes"],
                location=sv["location"],
                weather=sv["weather"],
                created_by=users.get(sv["created_by"]),
            )
        )
    await db.commit()
