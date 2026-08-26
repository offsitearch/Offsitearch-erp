"""Notifications module — in-app user notifications.

Owns: the ``notifications`` table (``Notification`` model), its CRUD API
(``/api/v1/notifications``) and business logic (list/mark-read/unread-count).

Public surface (the only symbols other modules may use):
    models.notification.Notification — the ORM model
    schemas.NotificationOut          — Pydantic output schema
    service                          — notify/list_mine/unread_count/mark_read/mark_all_read
    routes.router                    — FastAPI router mounted under /notifications
                                       (imported lazily by app.api, never at package init,
                                        to avoid import cycles with core auth deps)

Cross-module notes:
    * ``service.notify()`` is the de-facto cross-module messaging port: it is the
      way other domains deliver in-app notifications to users. Current consumers
      include the tasks, leaves and meetings domains.
    * This port will be formalized as ``NotifyPort`` in a later refactor step;
      until then, import it as
      ``from app.modules.notifications import service as notification_service``
      and call ``service.notify(...)``.
"""
