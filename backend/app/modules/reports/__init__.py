"""Reports module — projects, finance, and HR reports with export helpers.

Owns no tables: it is a read-only aggregator over other modules' aggregates
(projects, finance, people). Downstream of those domains by design.
"""
