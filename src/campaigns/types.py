import strawberry_django
from strawberry import auto

from src.campaigns.models import (
    Campaign,
    Category,
    Coverage,
    DataPoint,
    Measurement,
    District,
    MeasuringTool,
    Spreadsheet
)

@strawberry_django.type(Campaign)
class CampaignType:
    id: auto
    name: auto
    date: auto
    external_id: auto
    district: 'DistrictType'
    coverage: 'CoverageType'
    categories: list['CategoryType']
    data_points: list['DataPointType']
    measurements: list['MeasurementType']


@strawberry_django.type(Category)
class CategoryType:
    id: auto
    name: auto
    campaigns: list[CampaignType]


@strawberry_django.type(Coverage)
class CoverageType:
    id: auto
    name: auto
    campaigns: list[CampaignType]


@strawberry_django.type(DataPoint)
class DataPointType:
    id: auto
    name: auto
    campaign: CampaignType
    measurements: list['MeasurementType']


@strawberry_django.type(Measurement)
class MeasurementType:
    id: auto
    name: auto
    category: CategoryType
    data_point: DataPointType


@strawberry_django.type(District)
class DistrictType:
    id: auto
    name: auto
    campaigns: list[CampaignType]


@strawberry_django.type(MeasuringTool)
class MeasuringToolType:
    id: auto
    name: auto
    campaigns: list[CampaignType]


@strawberry_django.type(Spreadsheet)
class SpreadsheetType:
    id: auto
    name: auto
    campaigns: list[CampaignType]