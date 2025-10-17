# Standard imports
import re
# Django imports
from django.db import models
from django.utils import timezone
from django.apps import apps
# Project imports
from src.places.models import District
from src.logging_cfg import setup_logger


logger = setup_logger(__name__)

# Path Levels
PATH_LEVELS = [
    ("coverage", "coverage"),
    ("campaign", "campaign"),
    ("data_point", "data_point"),
    ("category", "category"),
    ("measurement", "measurement")
]

PATH_LEVELS_MODELS = {
    "coverage": "Coverage",
    "campaign": "Campaign",
    "data_point": "DataPoint",
    "category": "Category",
    "measurement": "Measurement"
}

PARENT_MAP = {
    "campaign": ("Coverage", "coverage_id"),
    "data_point": ("Campaign", "campaign_id"),
    "measurement": ("DataPoint", "data_point_id")
}


class BaseFile(models.Model):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    ftp_created_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scan_complete = models.BooleanField(default=False)
    is_unmatched = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True)

    def __str__(self) -> str:
        return str(self.name)

    def match_pattern(self) -> dict:
        rule_name = self._meta.model.__name__.lower()
        rules = PathRule.objects.filter(level=rule_name).order_by("order")
        for rule in rules:
            attributes = rule.match_pattern(self.name)
            if attributes:
                return attributes
        return None

    class Meta:
        abstract = True


# Measurements
class CategoryType():
    RAW_DATA = "Raw Data"
    TXT_DATA = "Text Data"
    PHOTOMETRY = "Photometry"
    RADIANCE = "Radiance"
    AVG_RADIANCE = "Average Radiance"
    TXT_RADIANCE = "Text Radiance"
    REFLECTANCE = "Reflectance"
    AVG_REFLECTANCE = "Average Reflectance"
    TXT_REFLECTANCE = "Text Reflectance"
    TXT_AVG_RADIANCE = "Text Average Radiance"
    TXT_AVG_REFLECTANCE = "Text Average Reflectance"
    RAD_PAR_CORR = "Radiance Parabolic Correction"
    TXT_RAD_PAR_CORR = "Text Radiance Parabolic Correction"
    REF_PAR_CORR = "Reflectance Parabolic Correction"
    TXT_REF_PAR_CORR = "Text Reflectance Parabolic Correction"

    CHOICES = (
        (RAW_DATA, RAW_DATA),
        (TXT_DATA, TXT_DATA),
        (PHOTOMETRY, PHOTOMETRY),
        # Radiance
        (RADIANCE, RADIANCE),
        (AVG_RADIANCE, AVG_RADIANCE),
        (TXT_RADIANCE, TXT_RADIANCE),
        (TXT_AVG_RADIANCE, TXT_AVG_RADIANCE),
        (RAD_PAR_CORR, RAD_PAR_CORR),
        (TXT_RAD_PAR_CORR, TXT_RAD_PAR_CORR),
        # Reflectance
        (REFLECTANCE, REFLECTANCE),
        (AVG_REFLECTANCE, AVG_REFLECTANCE),
        (TXT_REFLECTANCE, TXT_REFLECTANCE),
        (TXT_AVG_REFLECTANCE, TXT_AVG_REFLECTANCE),
        (REF_PAR_CORR, REF_PAR_CORR),
        (TXT_REF_PAR_CORR, TXT_REF_PAR_CORR),
    )
    SLUG_ALIASES = {
        PHOTOMETRY: ["fotometria"],
        RAW_DATA: ["datocrudo"],
        TXT_DATA: ["datotexto"],
        # Radiance aliases
        RADIANCE: ["radiancia", "datoradiancia"],
        RAD_PAR_CORR: ["radcorrpar", "radparcorr", "radianciacorrpar"],
        TXT_RAD_PAR_CORR: ["textoradianciacorrpar", "textoradcorrpar"],
        AVG_RADIANCE: ["radianciapromedio", "datoradianciapromedio"],
        TXT_RADIANCE: [
            "radianciatexto",
            "textoradiancia",
            "datoradianciatexto",
            "datotextoradiancia"
        ],
        TXT_AVG_RADIANCE: ["textoradianciapromedio", "radianciapromediotexto"],
        # Reflectance aliases
        REFLECTANCE: ["reflectancia", "datoreflectancia"],
        AVG_REFLECTANCE: ["reflectanciapromedio", "datoreflectanciapromedio"],
        TXT_REFLECTANCE: [
            "reflectanciatexto",
            "textoreflectancia",
            "datoreflectanciatexto",
            "datotextoreflectancia"
        ],
        TXT_AVG_REFLECTANCE: [
            "textoreflectanciapromedio",
            "reflectanciapromediotexto"
        ],
        REF_PAR_CORR: ["refcorrpar", "refparcorr", "reflectanciacorrpar"],
        TXT_REF_PAR_CORR: ["textoreflectanciacorrpar", "textorefcorrpar"],
    }

    @classmethod
    def get_by_alias(cls, alias: str) -> str:
        slug_alias = alias.lower().replace(" ", "")
        for category, aliases in cls.SLUG_ALIASES.items():
            if slug_alias in aliases:
                return category
        return None


class Category(models.Model):
    name = models.CharField(
        max_length=128,
        unique=True,
        choices=CategoryType.CHOICES
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.get_name_display()  # pylint: disable=no-member

    class Meta:
        verbose_name_plural = "Categories"


class MeasuringTool(models.Model):
    name = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255, null=True)
    fov = models.FloatField(null=True)
    measure_height = models.FloatField(null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.name + " " + self.model_name


# Campaigns
class Coverage(BaseFile):
    pass


class Campaign(BaseFile):
    # Fields
    date = models.DateField(null=True)
    external_id = models.CharField(max_length=255, null=True)
    # Relationships
    coverage = models.ForeignKey(
        Coverage, on_delete=models.CASCADE, related_name="campaigns"
    )
    district = models.ForeignKey(
        District,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    measuring_tool = models.ForeignKey(
        MeasuringTool,
        null=True,
        blank=True,
        related_name="campaigns",
        on_delete=models.SET_NULL
    )
    spreadsheets = models.ManyToManyField(
        "Spreadsheet",
        blank=True,
        related_name="campaigns"
    )

class DataPoint(BaseFile):
    # Fields
    order = models.IntegerField()
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    # Relationships
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="data_points"
    )

    def __str__(self) -> str:
        return f"{self.name} | {self.campaign}"


class Measurement(BaseFile):
    # Relationships
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    data_point = models.ForeignKey(
        "DataPoint", on_delete=models.CASCADE, related_name="measurements"
    )


# Spreadsheets
class SheetType():
    OFFICE = "Office Sheet"
    FIELD = "Field Sheet"

    CHOICES = (
        (OFFICE, "OFC"),
        (FIELD, "FLD"),
    )


class Spreadsheet(BaseFile):
    sheet_type = models.CharField(max_length=16, choices=SheetType.CHOICES)
    delimiter = models.CharField(max_length=1, default=";")


class ComplimentaryData(BaseFile):
    # Relationships
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="complimentary_data"
    )


class PathRule(models.Model):
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    pattern = models.CharField(max_length=255)
    date_format = models.CharField(max_length=255, null=True, blank=True)
    level = models.CharField(max_length=255, choices=PATH_LEVELS)

    def match_pattern(self, filename: str):
        match = re.match(self.pattern, filename)
        if match:
            groups = match.groupdict()
            result = {"metadata": {}}
            for key in groups:
                if key.startswith("metadata__"):
                    subkey = key.split("__")[1]
                    result["metadata"][subkey] = groups[key]
                else:
                    result[key] = groups[key]
            return result
        return None

    def get_model(self):
        model_name = str(self.level).capitalize()
        return apps.get_model("campaigns", model_name)

    def apply(self):
        model_class = self.get_model()
        unmatched_objects = model_class.objects.all()
        for obj in unmatched_objects:
            attributes = self.match_pattern(obj.name)
            if attributes:
                obj.create_matched_file(attributes)

    @classmethod
    def match_files(cls, files: list, level: str) -> list:
        rules = cls.objects.filter(level=level).order_by("order")
        matched_files = []
        unmatched_files = []
        for file_data in files:
            for rule in rules:
                attributes = rule.match_pattern(file_data["name"])
                if attributes:
                    file_data.update(attributes)
                    file_data["rule_id"] = rule.id
                    file_data["is_unmatched"] = False
                    matched_files.append(file_data)
                    break
            if file_data.get("is_unmatched", True):
                file_data["is_unmatched"] = True
                file_data["level"] = level
                logger.info("File %s is unmatched at level %s", file_data["name"], level)
                unmatched_files.append(file_data)
        return matched_files, unmatched_files

    def __str__(self) -> str:
        return str(self.name)


class UnmatchedObjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_unmatched=True)


class UnmatchedFile(BaseFile):
    parent_path = models.CharField(max_length=255)
    level = models.CharField(max_length=255, choices=PATH_LEVELS)
    objects = UnmatchedObjectManager()

    def create_matched_file(self, attributes: dict) -> BaseFile:
        model_name = PATH_LEVELS_MODELS.get(self.level)
        parent_model_name, parent_id_field = PARENT_MAP.get(self.level)
        file, created = None, False
        file_model = apps.get_model("campaigns", model_name)
        parent_model = apps.get_model("campaigns", parent_model_name)
        if attributes:
            parent_id = parent_model.objects.filter(
                path=self.parent_path
            ).first().id
            defaults = {
                "name": self.name,
                "description": self.description,
                "metadata": self.metadata,
                "ftp_created_at": self.ftp_created_at,
                "is_unmatched": False,
                parent_id_field: parent_id
            }
            defaults.update(attributes)
            file, created = file_model.objects.update_or_create(
                path=self.path,
                defaults=defaults
            )
            logger.info("UnmatchedFile %s matched to %s", self.name, model_name)
        return file, created
