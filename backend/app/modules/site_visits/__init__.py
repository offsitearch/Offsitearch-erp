"""Site visits module — field visit scheduling, photos, and PDF reports.

Owns: the ``site_visits`` and ``site_visit_photos`` tables (``SiteVisit``,
``SiteVisitPhoto`` models) and their CRUD API under ``/api/v1/site-visits``,
including photo upload/download and the per-visit PDF report.

Cross-module notes:
    * Validates the target project via the projects domain
      (future ProjectAccess contract).
    * Stores photos via core storage (app.core.storage).
"""
