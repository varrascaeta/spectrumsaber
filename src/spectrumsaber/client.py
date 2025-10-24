import requests
from src.logging_cfg import setup_logger

logger = setup_logger(__name__)
GRAPHQL_URL = "http://localhost:8000/graphql"


class SpectrumSaberClient:
    def __init__(self):
        self.__token__ = None
        self.__refresh_token__ = None

    def __get_headers__(self):
        headers = {"Content-Type": "application/json"}
        if self.__token__:
            headers["Authorization"] = f"JWT {self.__token__}"
        return headers

    def __refresh_auth_token__(self) -> bool:
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

    def query(self, query: str, variables: dict | None = None):
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

    def run_query(self, query: str):
        result = self.query(query)
        return result.get("data")
