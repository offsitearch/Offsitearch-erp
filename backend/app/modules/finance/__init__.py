"""Finance module — invoices, payments, expenses, financial overview, PDFs.

Owns: the ``invoices``, ``invoice_items`` and ``expenses`` tables (``Invoice``,
``InvoiceItem``, ``Expense`` models) and their business logic. Revenue
aggregates remain Director-restricted (see routes ``require_revenue_access``).
"""
