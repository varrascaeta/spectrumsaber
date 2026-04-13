"""
Server package — Django project and application layer.

Contains the Django project configuration (settings, URLs, WSGI/ASGI)
alongside the three application modules:

- campaigns: Field spectroscopy campaign data model and GraphQL API
- places:    Geographic entities (Country, Province, District)
- users:     Custom user model and JWT-based GraphQL authentication
"""
