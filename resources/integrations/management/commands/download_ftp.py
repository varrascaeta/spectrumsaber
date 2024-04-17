# Standard imports
from ftplib import FTP
from typing import Any
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str | None:
        logger.info("TESTING FTP CONNECTION")
