# Standard imports
import logging
from ftplib import FTP


logger = logging.getLogger(__name__)


class FTPClient():
    def __init__(self, host: str, username: str, password: str) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.connection = None

    def connect(self) -> FTP:
        if not self.connection:
            logger.info("Connecting to %s", self.host)
            self.connection = FTP(self.host, encoding="latin-1")
            status = self.connection.login(self.username, self.password)
            logger.info("Status: %s", status)
        else:
            logger.info("Already connected to %s", self.host)

    def get_files(self, path: str) -> list['str']:
        self.connect()
        logger.info("Scanning %s", path)
        files = self.connection.nlst(path)
        return files

    def __str__(self) -> str:
        return f"FTP:{self.username}@{self.host}"
