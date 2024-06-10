# Standard imports
import logging
# Django imports
from django.db import models
from django.utils import timezone
# Project imports
from resources.places.models import District

logger = logging.getLogger(__name__)


# Common utils
class BaseFile(models.Model):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    description = models.TextField(null=True)
    metadata = models.JSONField(null=True)
    ftp_created_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    @classmethod
    def matches_pattern(cls, filename: str) -> bool:
        raise NotImplementedError

    @classmethod
    def get_attributes_from_name(cls, filename: str) -> dict:
        raise NotImplementedError

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
    name = models.CharField(max_length=128, choices=CategoryType.CHOICES)
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
    @classmethod
    def matches_pattern(cls, filename: str) -> bool:
        return filename.isupper()

    @classmethod
    def get_attributes_from_name(cls, filename: str) -> dict:
        return {}


class Campaign(BaseFile):
    # Fields
    date = models.DateField(null=True)
    external_id = models.CharField(max_length=255, null=True)
    # Relationships
    coverage = models.ForeignKey(
        Coverage, on_delete=models.CASCADE, related_name="coverage_campaigns"
    )
    district = models.ForeignKey(
        District, null=True, on_delete=models.SET_NULL
    )
    measuring_tool = models.ForeignKey(
        MeasuringTool, null=True, related_name="campaigns",
        on_delete=models.SET_NULL
    )
    spreadsheets = models.ManyToManyField(
        "Spreadsheet", blank=True, related_name="campaigns"
    )

    @classmethod
    def matches_pattern(cls, filename: str) -> bool:
        splitted = filename.split("-")
        if len(splitted) >= 3:
            right_prefix = splitted[0].isdigit()
            right_date = len(splitted[1]) == 8
            return right_prefix and right_date
        return False

    @classmethod
    def get_attributes_from_name(cls, filename: str) -> dict:
        if cls.matches_pattern(filename):
            splitted = filename.split("-")
            return {
                "external_id": splitted[0],
                "date_str": splitted[1],
                "geo_code": splitted[2],
            }
        else:
            return {}


class DataPoint(BaseFile):
    # Fields
    order = models.IntegerField()
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    # Relationships
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="data_points"
    )

    @classmethod
    def matches_pattern(cls, filename: str) -> bool:
        cleaned_spaces = filename.replace(" ", "-")
        splitted = cleaned_spaces.split("-")
        if len(splitted) >= 2:
            right_prefix = splitted[0] == "Punto"
            right_order = splitted[1].isdigit()
            return right_prefix and right_order
        return False

    @classmethod
    def get_attributes_from_name(cls, filename: str) -> dict:
        if cls.matches_pattern(filename):
            splitted = filename.split("-")
            return {
                "order": int(splitted[1])
            }
        else:
            return {}

    def __str__(self) -> str:
        return f"{self.name} | {self.campaign}"


class Measurement(BaseFile):
    # Relationships
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    data_point = models.ForeignKey(
        "DataPoint", on_delete=models.CASCADE, related_name="measurements"
    )

    @classmethod
    def matches_pattern(cls, filename: str) -> bool:
        return True

    @classmethod
    def get_attributes_from_name(cls, filename: str) -> dict:
        return {}


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

    @classmethod
    def matches_pattern(cls, filename: str) -> bool:
        return True

    @classmethod
    def get_attributes_from_name(cls, filename: str) -> dict:
        return {}
