# schema.py

import strawberry
import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension

from src.campaigns.types import *

@strawberry.type
class Query:
    # Coverage
    coverage: CoverageType = strawberry_django.field(filters=CoverageFilter)
    coverages: list[CoverageType] = strawberry_django.field(filters=CoverageFilter)
    # Campaign
    campaign: CampaignType = strawberry_django.field(filters=CampaignFilter)
    campaigns: list[CampaignType] = strawberry_django.field(filters=CampaignFilter)
    # Data Point
    data_point: DataPointType = strawberry_django.field(filters=DataPointFilter)
    data_points: list[DataPointType] = strawberry_django.field(filters=DataPointFilter)
    # Category
    category: CategoryType = strawberry_django.field(filters=CategoryFilter)
    categories: list[CategoryType] = strawberry_django.field(filters=CategoryFilter)
    # Measurement
    measurement: MeasurementType = strawberry_django.field(filters=MeasurementFilter)
    measurements: list[MeasurementType] = strawberry_django.field(filters=MeasurementFilter)
    # District
    district: DistrictType = strawberry_django.field(filters=DistrictFilter)
    districts: list[DistrictType] = strawberry_django.field(filters=DistrictFilter)
    # Measuring Tool
    measuring_tool: MeasuringToolType = strawberry_django.field(filters=MeasuringToolFilter)
    measuring_tools: list[MeasuringToolType] = strawberry_django.field(filters=MeasuringToolFilter)
    # Spreadsheet
    spreadsheet: SpreadsheetType = strawberry_django.field(filters=SpreadsheetFilter)
    spreadsheets: list[SpreadsheetType] = strawberry_django.field(filters=SpreadsheetFilter )

schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension,  # not required, but highly recommended
    ],
)
