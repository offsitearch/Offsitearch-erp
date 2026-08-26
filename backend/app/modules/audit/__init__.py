"""Audit module — audit trail for all write operations.

Owns: the ``audit_logs`` table (``AuditLog`` model) and the audit query API.
Other modules record entries via ``log_audit``.
"""
