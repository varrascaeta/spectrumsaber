"""
SpectrumSaber GraphQL client module.

Contains: SpectrumSaberClient — JWT-authenticated GraphQL client.
"""

# Standard imports
import logging

# Third-party imports
import requests as _requests_module

# Project imports
from spectrumsaber.cfg import GRAPHQL_ENDPOINT, GRAPHQL_JWT_TOKEN

logger = logging.getLogger(__name__)


def _requests():
    """Return the requests module from spectrumsaber.client (patchable)."""
    import spectrumsaber.client as _c

    return _c.requests


class SpectrumSaberClient:
    def __init__(self):
        self.__token__ = GRAPHQL_JWT_TOKEN
        self.__refresh_token__ = None
        self.user = None
        self.updated_token = False

    def __get_headers__(self) -> dict:
        """
        Construct headers for GraphQL requests, including auth token
        if available.
        Returns:
            dict: Headers for the request.
        """
        headers = {"Content-Type": "application/json"}
        if self.__token__:
            headers["Authorization"] = f"JWT {self.__token__}"
        return headers

    def __refresh_auth_token__(self) -> bool:
        """
        Refresh the authentication token using the refresh token.
        Returns:
            bool: True if the token was refreshed successfully,
            False otherwise.
        """
        if not self.__refresh_token__:
            logger.error(
                "No refresh token available to refresh authentication. "
                "Please register or login with your credentials."
            )
            return False
        query = """
        mutation RefreshToken ($refreshToken: String!, $revokeRefreshToken: Boolean!) {
            refreshToken (refreshToken: $refreshToken, revokeRefreshToken: $revokeRefreshToken) {
                success
                token {
                    token
                }
                errors
            }
        }
        """  # noqa: E501
        variables = {
            "refreshToken": self.__refresh_token__,
            "revokeRefreshToken": False,
        }
        result = self.query(query, variables)
        if result.get("data") and result["data"]["refreshToken"]["success"]:
            self.__token__ = result["data"]["refreshToken"]["token"]["token"]
            logger.info("Refreshed token successfully.")
            return True
        else:
            logger.error("Failed to refresh token: %s", result.get("errors"))
            return False

    def __verify_token__(self) -> bool:
        """
        Verify if the current token is valid by attempting a simple query.
        Returns:
            bool: True if token is valid, False otherwise.
        """
        req = _requests()
        query = """
        query {
            me {
                id
                username
            }
        }
        """
        payload = {"query": query}
        try:
            resp = req.post(
                GRAPHQL_ENDPOINT,
                timeout=10,
                json=payload,
                headers=self.__get_headers__(),
            )
            data = resp.json()
            if data.get("errors"):
                return False
            if data.get("data") and data["data"].get("me"):
                self.user = data["data"]["me"]["username"]
                logger.info("Token verified for user: %s", self.user)
                return True
            return False
        except (_requests_module.RequestException, KeyError, ValueError) as e:
            logger.error("Error verifying token: %s", e)
            return False

    def query(self, query: str, variables: dict | None = None) -> dict:
        """
        Execute a GraphQL query or mutation.
        Args:
            query (str): The GraphQL query or mutation string.
            variables (dict | None): Optional variables for the query.
        Returns:
            dict: The JSON response from the server.
        """
        req = _requests()
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        resp = req.post(
            GRAPHQL_ENDPOINT,
            timeout=10,
            json=payload,
            headers=self.__get_headers__(),
        )
        data = resp.json()
        if data.get("errors"):
            for error in data["errors"]:
                if "Unauthenticated" in error.get("message", ""):
                    logger.warning("Token expired, attempting to refresh.")
                    refreshed = self.__refresh_auth_token__()
                    if refreshed:
                        return self.query(query, variables)
        return data

    def login(self, username: str, password: str):
        """
        Authenticate the user with the given credentials.
        First attempts to use GRAPHQL_JWT_TOKEN from environment if available.
        If the env token is expired, proceeds with username/password auth.
        If successful, stores the auth and refresh tokens.
        Args:
            username (str): The username.
            password (str): The password.
        """
        # First, try to use token from environment variable
        if GRAPHQL_JWT_TOKEN:
            logger.info("Found GRAPHQL_JWT_TOKEN in environment, verifying...")
            if self.__verify_token__():
                logger.info(
                    "Using valid token from GRAPHQL_JWT_TOKEN "
                    "environment variable."
                )
                return
            else:
                logger.warning(
                    "Token from GRAPHQL_JWT_TOKEN is expired or invalid. "
                    "Proceeding with username/password authentication."
                )
                self.__token__ = None
                self.updated_token = True

        # Proceed with normal login
        query = """
        mutation TokenAuth($username: String!, $password: String!) {
            tokenAuth(username: $username, password: $password) {
                success
                token {
                    token
                }
                errors
                refreshToken {
                    token
                }
            }
        }
        """
        variables = {
            "username": username,
            "password": password,
        }
        result = self.query(query, variables)
        if result.get("data") and result["data"].get("tokenAuth", {}).get(
            "success"
        ):
            token_data = result["data"]["tokenAuth"].get("token")
            refresh_data = result["data"]["tokenAuth"].get("refreshToken")
            self.__token__ = (
                token_data["token"]
                if token_data and "token" in token_data
                else None
            )
            self.__refresh_token__ = (
                refresh_data["token"]
                if refresh_data and "token" in refresh_data
                else None
            )
            logger.info("Authenticated user %s.", username)

            # Notify user to update their environment variable
            if self.updated_token:
                print(
                    "\n" + "=" * 60 + "\n"
                    "Your GRAPHQL_JWT_TOKEN has been refreshed.\n"
                    "Please update your environment variable with "
                    "the new token:\n"
                    "export GRAPHQL_JWT_TOKEN='%s'\n" % self.__token__
                    + "=" * 60
                )
        else:
            logger.error(
                "Failed to authenticate user %s: %s",
                username,
                result.get("errors"),
            )

    def run_query(self, query: str, params: dict | None = None) -> dict | None:
        """
        Run a GraphQL query and return the data.
        Args:
            query (str): The GraphQL query string.
            params (dict | None): The parameters for the query (if any).
        Returns:
            dict: The JSON response from the server.
        """
        result = self.query(query, params)
        return result

    def logout(self):
        """
        Clear authentication tokens to log out the user.
        """
        self.__token__ = None
        self.__refresh_token__ = None
        self.user = None
        logger.info("User logged out successfully.")

    def is_authenticated(self) -> bool:
        """
        Check if the client is currently authenticated.
        Returns:
            bool: True if authenticated, False otherwise.
        """
        return self.__token__ is not None

    def get_token(self) -> str | None:
        """
        Get the current authentication token.
        Returns:
            str | None: The current token or None if not authenticated.
        """
        return self.__token__

    def text2gql(self, llm_provider, cache_schema: bool = True):
        """
        Create a Text2GQL instance bound to this client.

        Args:
            llm_provider: Any LLMProvider instance (use
                ``spectrumsaber.llm.create_provider`` to build one).
            cache_schema: Cache the introspected schema between calls
                          (default: True).

        Returns:
            A :class:`~spectrumsaber.text2gql.Text2GQL` instance ready
            to translate and execute natural-language queries.
        """
        from spectrumsaber.text2gql import Text2GQL

        return Text2GQL(self, llm_provider, cache_schema=cache_schema)
