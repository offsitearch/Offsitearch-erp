"""Meetings module — meeting scheduling and RSVP tracking.

Owns: the ``meetings`` and ``meeting_attendees`` tables (``Meeting`` and
``MeetingAttendee`` models), their CRUD/RSVP API (``/api/v1/meetings``) and
business logic.

Public surface (the only symbols other modules may use):
    models.Meeting / models.MeetingAttendee   — the ORM models
    service                — list/create/update/delete/rsvp functions
    routes.router          — FastAPI router mounted under /meetings
                             (imported lazily by app.api, never at package init,
                             to avoid import cycles with core auth deps)

Cross-module notes:
    * Reads ``User.name``/``User.email`` for organizer and attendee display via
      read-only joins (identity domain).
    * Sends invitation notifications through the shared notification port
      (transitionally still ``app.services.notification_service``).
    * Emits audit events through the shared audit port.
"""
