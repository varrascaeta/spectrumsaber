"""
Campaigns Django application.

Manages the core domain model for field spectroscopy campaigns:
Coverage → Campaign → DataPoint → Measurement hierarchy, with
pattern-based path matching (PathRule), complimentary data types,
and a GraphQL query API.
"""
