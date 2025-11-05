# Standard imports
import logging
import os
import re
import signal
from datetime import UTC, datetime
from ftplib import FTP, error_perm

# Third party imports
import requests

# Project imports
from spectrumsaber.cfg import (
    FTP_HOST,
    FTP_PASSWORD,
    FTP_USER,
    GRAPHQL_ENDPOINT,
)

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)
DIR_LIST_PATTERN = (
    r"^(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?:AM|PM))\s+" r"(<DIR>|\d+)\s+(.+)$"
)  # noqa: E501
DATE_FORMAT = "%m-%d-%y"
TIME_FORMAT = "%I:%M%p"


# Class definitions
class TimeoutException(Exception):
    pass


class TimeoutContext:
    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def __enter__(self):
        logger.info("Setting timeout to %s seconds", self.timeout)
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)

    def handler(self, signum, frame):
        raise TimeoutException("Timeout ocurred")


class FTPClient:
    def __init__(
        self,
        ftp_user: str = FTP_USER,
        ftp_password: str = FTP_PASSWORD,
        ftp_host: str = FTP_HOST,
    ) -> None:
        for required, name in [
            (ftp_host, "FTP_HOST"),
            (ftp_user, "FTP_USER"),
            (ftp_password, "FTP_PASSWORD"),
        ]:
            if not required:
                raise ValueError(f"{name} not set")
        self.host = ftp_host
        self.username = ftp_user
        self.password = ftp_password
        self.connection = None

    def __enter__(self):
        with TimeoutContext(30):
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.quit()

    def connect(self) -> FTP:
        """
        Connect to the FTP server using provided credentials.
        Returns:
            FTP: An active FTP connection.
        """
        logger.info("Connecting to %s", self.host)
        if not self.connection:
            self.connection = FTP(self.host, encoding="latin-1")
        status = self.connection.login(self.username, self.password)
        logger.info("Status: %s", status)

    def level_up(self) -> None:
        """
        Move up one directory level on the FTP server.
        """
        self.connection.cwd("..")

    def get_dir_data(self, path: str) -> list[dict]:
        """
        Retrieve and parse directory listing from the FTP server.
        Args:
            path (str): The directory path to scan.
        Returns:
            list[dict]: A list of parsed file and directory information.
        """
        try:
            logger.info("Scanning %s", path)
            lines = []
            self.connection.dir(path, lines.append)
            parsed_files = []
            for line in lines:
                parsed = self.parse_line(path, line)
                if parsed:
                    parsed_files.append(parsed)
            return parsed_files
        except error_perm as e:
            logger.error("Error scanning %s: %s", path, e)
            with open("permission_errors.txt", "a", encoding="utf-8") as f:
                f.write(f"{path}\n")
            return []
        except Exception as e:
            logger.error("Error scanning %s: %s", path, e)
            return []

    def parse_line(self, path: str, line: str) -> dict:
        """
        Parse a line from the FTP directory listing.
        Args:
            path (str): The directory path.
            line (str): A line from the directory listing.
        Returns:
            dict: Parsed file or directory information.
        """
        match = re.match(DIR_LIST_PATTERN, line.strip())
        if match:
            date_str, time_str, kind, filename = match.groups()
            date = datetime.strptime(date_str, DATE_FORMAT).date()
            time = datetime.strptime(time_str, TIME_FORMAT).time()
            created_at = datetime.combine(date, time).replace(tzinfo=UTC)
            return {
                "name": filename,
                "path": os.path.join(path, filename),
                "created_at": created_at,
                "is_dir": kind == "<DIR>",
            }
        else:
            logger.error("Line  %s does not match FTP pattern", line)
            return {}

    def get_files_at_depth(self, path: str, depth: int) -> list[dict]:
        """
        Retrieve files at a specified depth from the given path.
        Depth 0 means the root path relative to BASE_FTP_PATH from env.
        Args:
            path (str): The starting directory path.
            depth (int): The depth to scan.
        Returns:
            list[dict]: A list of files found at the specified depth.
        """
        current_depth = 0
        files = []
        while current_depth < depth:
            current_files = self.get_dir_data(path)
            for file in current_files:
                if file["is_dir"]:
                    files.extend(self.get_files_at_depth(file["path"], depth))
                else:
                    files.append(file)
            current_depth += 1
        return files

    def __str__(self) -> str:
        return f"FTP:{self.username}@{self.host}"


class SpectrumSaberClient:
    def __init__(self):
        self.__token__ = None
        self.__refresh_token__ = None
        self.user = None

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
            self.__refresh_token__ = result["data"]["tokenAuth"][
                "refreshToken"
            ]["token"]
            logger.info("Authenticated user %s.", username)
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
