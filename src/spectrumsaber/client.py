# Standard imports
import requests
import logging
# Third party imports
from airflow.api.client.local_client import Client
# Local imports
from src.users.models import SpectrumsaberUser

logger = logging.getLogger(__name__)
GRAPHQL_URL = "http://localhost:8000/graphql"


class SpectrumSaberClient:
    def __init__(self):
        self.__token__ = None
        self.__refresh_token__ = None
        self.user = None

    def __get_headers__(self) -> dict:
        """
        Construct headers for GraphQL requests, including auth token if available.
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
            bool: True if the token was refreshed successfully, False otherwise.
        """
        if not self.__refresh_token__:
            logger.error(
                "No refresh token available to refresh authentication. " \
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
        """
        variables = {
            "refreshToken": self.__refresh_token__,
            "revokeRefreshToken": False
        }
        result = self.query(query, variables)
        if result.get("data") and result["data"]["refreshToken"]["success"]:
            self.__token__ = result["data"]["refreshToken"]["token"]["token"]
            logger.info("Refreshed token successfully.")
            return True
        else:
            logger.error("Failed to refresh token: %s", result.get("errors"))
            return False

    def get_user(self, username: str) -> SpectrumsaberUser:
        """
        Retrieve the SpectrumsaberUser instance for the given username.
        Args:
            username (str): The username of the user to retrieve.
        Returns:
            SpectrumsaberUser: The user instance.
        """
        if not self.user:
            self.user = SpectrumsaberUser.objects.get(username=username)
        return self.user

    def query(self, query: str, variables: dict | None = None) -> dict:
        """
        Execute a GraphQL query or mutation.
        Args:
            query (str): The GraphQL query or mutation string.
            variables (dict | None): Optional variables for the query.
        Returns:
            dict: The JSON response from the server.
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        resp = requests.post(
            GRAPHQL_URL,
            timeout=10,
            json=payload,
            headers=self.__get_headers__()
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

    def register(self, username: str, email: str, password: str, password_confirmation: str):
        """
        Register a new user with the given credentials.
        Args:
            username (str): The desired username.
            email (str): The user's email address.
            password (str): The desired password.
            password_confirmation (str): Confirmation of the desired password.
        Returns:
            dict: The JSON response from the server.
        """
        query = """
        mutation Register($username: String!, $email: String!, $password1: String!, $password2: String!) {
            register(username: $username, email: $email, password1: $password1, password2: $password2) {
                success
                errors
            }
        }
        """
        variables = {
            "username": username,
            "email": email,
            "password1": password,
            "password2": password_confirmation,
        }
        result = self.query(query, variables)
        if result.get("errors"):
            logger.error("Error registering user %s: %s", username, result["errors"])
        elif result.get("data") and result["data"]["register"]["success"]:
            logger.info("Registered user %s successfully.", username)
        return result

    def login(self, username: str, password: str):
        """
        Authenticate the user with the given credentials.
        If successful, stores the auth and refresh tokens.
        Args:
            username (str): The username.
            password (str): The password.
        """
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
        if result.get("data") and result["data"]["tokenAuth"]["success"]:
            self.__token__ = result["data"]["tokenAuth"]["token"]["token"]
            self.__refresh_token__ = result["data"]["tokenAuth"]["refreshToken"]["token"]
            logger.info("Authenticated user %s.", username)
        else:
            logger.error("Failed to authenticate user %s: %s", username, result.get("errors"))

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

    def get_dags(self) -> dict | None:
        """
        Retrieve the list of available DAGs from the server.
        Returns:
            dict: The JSON response from the server.
        """
        query = """
        query {
            getDags {
                dagId
                dagDisplayName
                isActive
                isPaused
                tags
                description
            }
        }
        """
        result = self.query(query)
        return result

    def get_dag_info(self, dag_id: str) -> dict | None:
        """
        Retrieve information about a specific DAG by its ID.
        Args:
            dag_id (str): The ID of the DAG to retrieve.
        Returns:
            dict: The JSON response from the server.
        """
        query = """
        query getDagInfo($dagId: String!) {
            getDagInfo(dagId: $dagId) {
                dagId
                dagDisplayName
                isActive
                isPaused
                tags
                description
                params {
                    name
                    type
                    description
                }
            }
        }
        """
        variables = {
            "dagId": dag_id
        }
        result = self.query(query, variables)
        return result

    def trigger_dag(self, dag_id: str, params: dict) -> str:
        """
        Trigger an Airflow DAG run by its ID.
        Args:
            dag_id (str): The ID of the DAG to trigger.
        Returns:
            dict: The JSON response from the server.
        """
        query = """
        mutation TriggerDAG($dagId: String!, $params: [KeyValueInput!]!) {
            triggerDag(dagId: $dagId, params: $params)
        }
        """
        variables = {
            "dagId": dag_id,
            "params": params
        }
        result = self.query(query, variables)
        return result
