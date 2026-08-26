"""Holidays module — company holiday calendar.

Owns: the ``holidays`` table (``Holiday`` model), its CRUD API
(``/api/v1/holidays``) and business logic.

Public surface (the only symbols other modules may use):
    models.Holiday         — the ORM model
    service                — list/create/update/delete functions
    routes.router          — FastAPI router mounted under /holidays
                             (imported lazily by app.api, never at package init,
                              to avoid import cycles with core auth deps)

Cross-module notes:
    * Consumed indirectly by the leave/payroll domains for working-day
      calculations; these will migrate to a ``HolidayCalendar`` contract
      owned by this module.
"""
