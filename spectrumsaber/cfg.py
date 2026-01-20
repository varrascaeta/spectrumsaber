import os

# FTP Credentials
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASSWORD = os.getenv("FTP_PASSWORD")

# GraphQL Endpoint
GRAPHQL_ENDPOINT = os.getenv(
    "GRAPHQL_ENDPOINT", "http://localhost:8000/graphql/"
)
