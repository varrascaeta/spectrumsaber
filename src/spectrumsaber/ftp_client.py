# Standard imports
import json
import logging
import os
import re
import signal
from datetime import datetime, UTC
# Extra imports
from ftplib import FTP, error_perm


logger = logging.getLogger(__name__)
DIR_LIST_PATTERN = (
    r'^(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?:AM|PM))\s+'
    r'(<DIR>|\d+)\s+(.+)$'
)
DATE_FORMAT = "%m-%d-%y"
TIME_FORMAT = "%I:%M%p"


# Class definitions
class TimeoutException(Exception):
    pass


class TimeoutContext():
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


class FTPClient():
    def __init__(self) -> None:
        ftp_user = os.getenv("FTP_USER")
        ftp_password = os.getenv("FTP_PASSWORD")
        ftp_host = os.getenv("FTP_HOST")
        if not ftp_host:
            raise ValueError("FTP_HOST not set")
        if not ftp_user or not ftp_password:
            raise ValueError("FTP_USER or FTP_PASSWORD not set")
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
        logger.info("Connecting to %s", self.host)
        if not self.connection:
            self.connection = FTP(self.host, encoding="latin-1")
        status = self.connection.login(self.username, self.password)
        logger.info("Status: %s", status)

    def level_up(self) -> None:
        self.connection.cwd("..")

    def get_dir_data(self, path: str) -> list[dict]:
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

    def parse_line(self, path, line):
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
