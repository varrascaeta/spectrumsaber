# Standard imports
import logging
from ftplib import FTP
import re
import os
from datetime import datetime


logger = logging.getLogger(__name__)
DIR_LIST_PATTERN = (
    r'^(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?:AM|PM))\s+'
    r'(<DIR>|\d+)\s+(.+)$'
)
DATE_FORMAT = "%m-%d-%y"
TIME_FORMAT = "%I:%M%p"


class FTPClient():
    def __init__(self, host: str, username: str, password: str) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.connection = None

    def connect(self) -> FTP:
        logger.info("Connecting to %s", self.host)
        self.connection = FTP(self.host, encoding="latin-1")
        status = self.connection.login(self.username, self.password)
        logger.info("Status: %s", status)

    def get_files(self, path: str) -> list['dict']:
        self.connect()
        logger.info("Scanning %s", path)
        self.connection.cwd(path)
        lines = []
        self.connection.dir(lines.append)
        self.connection.quit()
        parsed_files = [self.parse_line(path, line) for line in lines]
        return parsed_files

    def parse_line(self, path, line):
        match = re.match(DIR_LIST_PATTERN, line.strip())
        if match:
            date_str, time_str, kind, filename = match.groups()
            date = datetime.strptime(date_str, DATE_FORMAT).date()
            time = datetime.strptime(time_str, TIME_FORMAT).time()
            created_at = datetime.combine(date, time)
            return {
                "filepath": os.path.join(path, filename),
                "created_at": created_at,
                "is_dir": kind == "<DIR>",
            }
        else:
            logger.error(f"Line {line} does not match pattern")
            return {}

    def __str__(self) -> str:
        return f"FTP:{self.username}@{self.host}"
