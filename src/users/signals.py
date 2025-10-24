# Standard library imports
import logging
# Django imports
from django.db.models.signals import post_save
from django.dispatch import receiver
# GQL Auth imports
from gqlauth.models import UserStatus
# Project imports
from src.users.models import SpectrumsaberUser


logger = logging.getLogger(__name__)

@receiver(post_save, sender=SpectrumsaberUser)
def auto_verify_user(sender, instance, created, **kwargs):
    if created:
        user_status, created = UserStatus.objects.update_or_create(
            user=instance,
            defaults={
                "verified": True,
            }
        )
        logger.info("Verified user %s automatically.", instance.username)
