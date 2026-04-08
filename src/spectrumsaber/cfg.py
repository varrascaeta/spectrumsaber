"""
Configuration loader for the SpectrumSaber CLI.

Reads FTP credentials (FTP_HOST, FTP_USER, FTP_PASSWORD) and the
GraphQL endpoint (GRAPHQL_ENDPOINT, GRAPHQL_JWT_TOKEN) from environment
variables, with optional .env file support via python-dotenv.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# FTP Credentials
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASSWORD = os.getenv("FTP_PASSWORD")

# GraphQL Endpoint
GRAPHQL_ENDPOINT = os.getenv(
    "GRAPHQL_ENDPOINT", "http://localhost:8000/graphql/"
)

# GraphQL JWT Token (optional, for pre-authenticated sessions)
GRAPHQL_JWT_TOKEN = os.getenv("GRAPHQL_JWT_TOKEN")
