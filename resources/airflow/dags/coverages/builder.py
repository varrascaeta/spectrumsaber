
# Standard imports
from datetime import datetime
# Project imports
from resources.campaigns.models import Coverage


class CoverageBuilder:
    def build(self, coverage_data: dict) -> Coverage:
        name = coverage_data["name"]
        path = coverage_data["path"]
        created_at = datetime.fromisoformat(coverage_data["created_at"])
        if Coverage.matches_pattern(name):
            coverage, created = Coverage.objects.update_or_create(
                name=name,
                path=path,
                defaults={"ftp_created_at": created_at},
            )
            return coverage
