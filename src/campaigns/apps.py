from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.campaigns"

    def ready(self):
        import src.campaigns.signals  # noqa
