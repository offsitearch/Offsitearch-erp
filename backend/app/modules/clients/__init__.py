"""Clients (CRM) module — client records and communication tracking.

Owns: the ``clients`` and ``client_communications`` tables (``Client`` and
``ClientCommunication`` models), the ``/api/v1/clients`` CRUD + profile +
communications API, and their business logic.

Public surface (the only symbols other modules may use):
    models.client.Client / models.client.ClientCommunication — the ORM models
    service                — CRUD/search/profile/communication functions
    routes.router          — FastAPI router mounted under /clients
                             (imported lazily by app.api, never at package init,
                             to avoid import cycles with core auth deps)

Cross-module notes:
    * The client profile aggregation reads Project (projects domain) and joins
      ``User.name`` (identity domain) read-only — transitional cross-domain
      reads; future lookup contracts will replace them.
"""
