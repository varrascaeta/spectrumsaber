"""
FTP client module for SpectrumSaber.

Contains: DIR_LIST_PATTERN, DATE_FORMAT, TIME_FORMAT,
          TimeoutException, TimeoutContext, FTPClient.
"""

# Standard imports
import logging
import os
import re
from datetime import UTC, datetime
from ftplib import FTP, error_perm

# Project imports
from spectrumsaber.cfg import FTP_HOST, FTP_PASSWORD, FTP_USER

logger = logging.getLogger(__name__)

DIR_LIST_PATTERN = (
    r"^(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?:AM|PM))\s+" r"(<DIR>|\d+)\s+(.+)$"
)
DATE_FORMAT = "%m-%d-%y"
TIME_FORMAT = "%I:%M%p"


class TimeoutException(Exception):
    pass


class TimeoutContext:
    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def __enter__(self):
        import spectrumsaber.client as _client

        logger.info("Setting timeout to %s seconds", self.timeout)
        _client.signal.signal(_client.signal.SIGALRM, self.handler)
        _client.signal.alarm(self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import spectrumsaber.client as _client

        _client.signal.alarm(0)

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
        import spectrumsaber.client as _client

        with _client.TimeoutContext(30):
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
        import spectrumsaber.client as _client

        logger.info("Connecting to %s", self.host)
        if not self.connection:
            self.connection = _client.FTP(self.host, encoding="latin-1")
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
        except OSError as e:
            logger.error("Error scanning %s: %s", path, e)
            return []
        except Exception as e:
            logger.error("Unexpected error scanning %s: %s", path, e)
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

    def get_files_at_depth(
        self, path: str, max_depth: int, current_depth: int = 0
    ) -> list[dict]:
        """
        Retrieve files at a specified depth from the given path.
        Depth 0 means the root path relative to BASE_FTP_PATH from env.
        Args:
            path (str): The starting directory path.
            max_depth (int): The maximum depth to scan.
            current_depth (int): The current depth in the recursion.
        Returns:
            list[dict]: A list of files found at the specified depth.
        """
        files = []
        while current_depth < max_depth:
            current_files = self.get_dir_data(path)
            current_depth += 1
            for file in current_files:
                if file["is_dir"]:
                    files.extend(
                        self.get_files_at_depth(
                            file["path"], max_depth, current_depth
                        )
                    )
                else:
                    files.append(file)
        return files

    def __str__(self) -> str:
        return f"FTP:{self.username}@{self.host}"
