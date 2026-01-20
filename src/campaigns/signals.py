# Django imports
from django.db.models.signals import post_save
from django.dispatch import receiver

# Project imports
from src.campaigns.models import PathRule, UnmatchedFile
from src.logging_cfg import setup_logger

logger = setup_logger(__name__)


@receiver(post_save, sender=PathRule)
def match_new_patterns(sender, instance: PathRule, created, **kwargs):
    unmatched_files = UnmatchedFile.objects.filter(level=instance.level)
    for unmatched in unmatched_files:
        attributes = instance.match_pattern(unmatched.name)
        if attributes:
            file, created = unmatched.create_matched_file(attributes)
            if file:
                logger.info(
                    "Created matched file %s for UnmatchedFile %s",
                    file.name,
                    unmatched.name,
                )
                unmatched.delete()
