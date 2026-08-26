"""Settings module — system-wide key/value configuration store.

Owns: the ``settings`` table (``Setting`` model, unique per (group, key)),
its CRUD API under ``/api/v1/settings`` (admin-only) and business logic,
plus ``get_studio_info`` used by PDF-generating modules.

Public surface (the only symbols other modules may use):
    models.Setting         — the ORM model
    schemas                — SettingOut / SettingUpsertIn
    service                — list/upsert/delete/get_studio_info functions
    routes.router          — FastAPI router mounted under /settings
                             (imported lazily by app.api, never at package init)

Cross-module notes:
    * The attendance and leave domains read ``Setting`` rows directly at
      runtime; they will migrate to a SettingsPort contract owned by this
      module.
"""
