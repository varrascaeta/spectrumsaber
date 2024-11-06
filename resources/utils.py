# Standard imports
import importlib
import json
import logging
import os
import re
import sys
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
        credentials_path = os.getenv("FTP_CREDENTIALS_FILEPATH")
        if not credentials_path:
            raise ValueError("FTP_CREDENTIALS_FILEPATH not set")
        else:
            credentials = json.load(open(credentials_path))
        self.host = credentials["host"]
        self.username = credentials["username"]
        self.password = credentials["password"]
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
            logger.error(f"Error scanning {path}: {e}")
            with open("permission_errors.txt", "a") as f:
                f.write(f"{path}\n")
            return []
        except Exception as e:
            logger.error(f"Error scanning {path}: {e}")
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
            logger.error(f"Line {line} does not match FTP pattern")
            return {}

    def recursive_scan(self, start_path: str) -> dict:
        result = {}
        subdirs = self.get_dir_data(start_path)
        for subdir in subdirs:
            filename = subdir["name"]
            if subdir["is_dir"]:
                result[filename] = self.map_to_json(subdir["path"])
            else:
                if result.get(filename):
                    result[filename].append(subdir["path"])
                else:
                    result[filename] = [filename]
        return result

    def map_to_json(self, start_path: str) -> list[dict]:
        ftp_structure = self.recursive_scan(start_path)
        with open("ftp_structure.json", "w") as f:
            json.dump(ftp_structure, f, default=str)
        logger.info("FTP structure saved to ftp_structure.json")

    def __str__(self) -> str:
        return f"FTP:{self.username}@{self.host}"


class DatabaseContext():
    def __enter__(self):
        sys.path.append('./spectrumsaber/')  # TODO: Change this to env var
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service.settings")
        import django
        django.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def dynamic_import(module: str, name: str):
    module = importlib.import_module(module)
    return getattr(module, name)


def get_dirs_to_process(self, filepath: str) -> list[str]:
    with open(filepath) as f:
        return json.load(f)
