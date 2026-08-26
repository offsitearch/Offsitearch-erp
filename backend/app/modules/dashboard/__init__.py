"""Dashboard module — org summary aggregation endpoint.

Owns no tables: it composes counts across attendance, projects, tasks,
invoices and users in one place. This is the sanctioned cross-domain read
model; other modules must not replicate this pattern.
"""
