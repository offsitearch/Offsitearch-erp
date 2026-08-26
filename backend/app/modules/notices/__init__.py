"""Notices module — company notice/announcement board.

Owns: the ``notices`` table (``Notice`` model), its CRUD API (``/api/v1/notices``)
and business logic.

Public surface (the only symbols other modules may use):
    models.notice.Notice   — the ORM model
    service                — list/create/update/soft_delete functions
    routes.router          — FastAPI router mounted under /notices
                             (imported lazily by app.api, never at package init,
                              to avoid import cycles with core auth deps)

Cross-module notes:
    * Reads ``User.name`` for author display via a read-only join (identity domain).
    * Emits audit events through the shared audit port.
"""
